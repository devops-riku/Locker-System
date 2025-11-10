from machine import Pin, SPI, I2C
import network, time, uos, _thread, machine, gc, ntptime
try:
    import ujson as json  # Use ujson if available (MicroPython)
except ImportError:
    import json  # Fall back to standard json
from microdot import Microdot, Response
from mfrc522 import MFRC522
from keypad_matrix import Keypad
from umqtt.simple import MQTTClient
from i2c_lcd import I2cLcd

# ==== Disable WDT and Brownout to Prevent Boot Errors ====
import esp
esp.osdebug(None)  # Disable OS debug messages

# Lower CPU frequency during boot to reduce power draw
machine.freq(160000000)  # 160MHz instead of 240MHz (reduces brownout)

# ==== Buzzer Setup ====
BUZZER_PIN = 32                 
# For 5V active buzzer module: HIGH = ON, LOW = OFF (most common)
# If your buzzer is opposite, change BUZZER_ACTIVE_LEVEL to 0
BUZZER_ACTIVE_LEVEL = 1         # Active HIGH for 5V buzzer module
buzzer = Pin(BUZZER_PIN, Pin.OUT, value=0)  # Start with buzzer OFF (LOW)

def buzz(n=1, on_ms=120, off_ms=90):
    """Buzzer function for 5V active buzzer module"""
    for _ in range(n):
        buzzer.value(BUZZER_ACTIVE_LEVEL)    # Turn buzzer ON (HIGH)
        time.sleep_ms(on_ms)
        buzzer.value(1 - BUZZER_ACTIVE_LEVEL)  # Turn buzzer OFF (LOW)
        if _ < n - 1:  # Don't wait after the last buzz
            time.sleep_ms(off_ms)

# Initial test beep after a small delay to ensure proper initialization
time.sleep_ms(300)  # Longer delay for power stabilization
buzz(1, 500)  # Single long beep on startup
time.sleep_ms(200)  # Additional stabilization time

# ==== Configuration ====
RELAY_GPIO_MAP = {15: Pin(15, Pin.OUT), 4: Pin(4, Pin.OUT)}
UNLOCK_DURATION = 3
AP_SSID = "ESP32-Config"
AP_PASSWORD = "12345678"
WIFI_CONFIG_PATH = "wifi_config.txt"
AUTH_CONFIG_PATH = "auth_config.json"
HISTORY_BUFFER_PATH = "history_buffer.json"
MAX_HISTORY_BUFFER = 100  # Maximum number of offline events to store
MQTT_BROKER = "a26bb47bf62f46468d153a09fbffa641.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "esp32_locker_1"
MQTT_USERNAME = "rikumqtt"
MQTT_PASSWORD = "@Riku01234"
MQTT_TOPIC_SUB = b"locker/control"
MQTT_TOPIC_PUB = b"locker/status"
MQTT_TOPIC_VALIDATE_PIN = b"locker/validate_pin"
MQTT_TOPIC_LOCKDOWN = b"locker/lockdown"

mqtt_client = None
pin_buffer = ""
SERVER_URL = "https://locker-system.up.railway.app"
current_display = None
MAX_FAILED_ATTEMPTS = 3
LOCK_DURATION = 120  # 2 minutes in seconds
failed_pin_attempts = 0
locked_until_time = 0

# ==== LCD Setup ====
i2c = I2C(0, scl=Pin(16), sda=Pin(17), freq=400000)
lcd = None
try:
    time.sleep_ms(200)  # Give I2C bus time to stabilize
    devices = i2c.scan()
    if devices:
        lcd_addr = devices[0]
        lcd = I2cLcd(i2c, lcd_addr, 4, 20)
        time.sleep_ms(100)  # Allow LCD to initialize
        lcd.clear()
        lcd.putstr("Initializing...")
    else:
        print("No I2C devices found")
except Exception as e:
    print("LCD init failed:", e)

for relay in RELAY_GPIO_MAP.values():
    relay.value(1)

# ==== Lockout Handling ====
def is_system_locked():
    return time.time() < locked_until_time

def handle_pin_validation(payload):
    global locked_until_time
    try:
        data = json.loads(payload)
        user_id = str(data.get("user_id"))
        duration = data.get("lockout_duration")
        source = data.get("source", "web")

        print(f"Received lockout from {source} - duration: {duration}")

        # If duration is a number (seconds), use it directly
        if isinstance(duration, (int, float)):
            locked_until_time = time.time() + duration
            print(f"System locked for {duration} seconds")
        else:
            # If duration is a formatted time string, ignore it and use local lockout
            print("Ignoring server duration, using local 2-minute lockout")
            locked_until_time = time.time() + LOCK_DURATION  # Use local 2-minute lockout

        print(f"Lockout for user {user_id} - locked until timestamp: {locked_until_time}")

        # Update the display
        if lcd:
            lcd.clear()
            lcd.putstr(f"System is Locked!")
            lcd.move_to(0, 1)
            if source == "web":
                lcd.putstr(f"Web initiated lock")
            else:
                lcd.putstr(f"Try again later!!")

        buzz(3, 200, 200)  # Three warning beeps

        # Start countdown display thread if not hardware initiated
        if source == "web":
            _thread.start_new_thread(show_lockout_countdown, ())

    except Exception as e:
        print("Error handling pin validation:", e)

def record_pin_failure():
    global failed_pin_attempts, locked_until_time

    failed_pin_attempts += 1
    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_pin_attempts
    
    buzz(2, 150, 100)  # Two error beeps

    if failed_pin_attempts >= MAX_FAILED_ATTEMPTS:
        # Lock for exactly 2 minutes (120 seconds)
        locked_until_time = time.time() + LOCK_DURATION
        
        print(f"🔒 System locked for {LOCK_DURATION} seconds (2 minutes)")

        # Send MQTT notification with local lock duration to both validation and lockdown topics
        try:
            lockers = load_auth()
            for user_id, locker in lockers.items():
                payload = json.dumps({
                    "type": "hardware_lockdown",
                    "user_id": int(user_id),
                    "lockout_seconds": LOCK_DURATION,
                    "lockout_duration": LOCK_DURATION,  # For backwards compatibility
                    "end_time": locked_until_time,
                    "source": "hardware",
                    "message": f"System locked for {LOCK_DURATION} seconds due to failed PIN attempts"
                })
                if mqtt_client:
                    # Send to both topics to ensure web system receives it
                    mqtt_client.publish("locker/validate_pin", payload)
                    mqtt_client.publish("locker/lockdown", payload)
                    print("📤 Hardware lockdown info sent via MQTT:", payload)
        except Exception as e:
            print("❌ Failed to publish hardware lockdown info:", e)

        failed_pin_attempts = 0

        if lcd:
            lcd.clear()
            lcd.putstr("Too many wrong PINs")
            lcd.move_to(0, 1)
            lcd.putstr("Locked for 2 mins")
        
        buzz(5, 100, 100)  # Five rapid warning beeps for lockout

        _thread.start_new_thread(show_lockout_countdown, ())

    else:
        print(f"❌ Wrong PIN. {remaining_attempts} attempts left")
        if lcd:
            lcd.clear()
            lcd.putstr(f"Wrong PIN")
            lcd.move_to(0, 1)
            lcd.putstr(f"Attempts left: {remaining_attempts}")
        time.sleep(2)
        show_pin_entry_display()

def show_lockout_countdown():
    """Show countdown during lockout period"""
    while is_system_locked():
        remaining_time = int(locked_until_time - time.time())
        
        # Ensure we don't show negative time
        if remaining_time <= 0:
            break
            
        mins, secs = divmod(remaining_time, 60)
        
        if lcd:
            lcd.clear()
            lcd.putstr(f"System Locked")
            lcd.move_to(0, 1)
            lcd.putstr(f"Time left: {mins:02d}:{secs:02d}")
        
        time.sleep(1)
    
    # When lockout period is over
    print("🔓 Lockout period expired")
    if lcd:
        lcd.clear()
        lcd.putstr("Lock expired")
        lcd.move_to(0, 1)
        lcd.putstr("You may retry now")
    buzz(2, 200, 200)  # Two beeps to indicate unlock
    time.sleep(2)
    show_default_display()

# ==== Additional function to manually reset lockout (for testing/emergency) ====
def reset_lockout():
    """Emergency function to reset lockout - can be called via MQTT or web interface"""
    global locked_until_time, failed_pin_attempts
    locked_until_time = 0
    failed_pin_attempts = 0
    print("🔓 Lockout manually reset")
    if lcd:
        lcd.clear()
        lcd.putstr("Lockout Reset")
        time.sleep(1)
        show_default_display()
    buzz(1, 500)  # Single long beep for reset confirmation

def show_default_display():
    if lcd:
        lcd.clear()
        lcd.putstr("Scan RFID:")
        lcd.move_to(0, 1)
        lcd.putstr("Input PIN:")

def show_pin_entry_display():
    if lcd:
        lcd.clear()
        lcd.putstr("Scan RFID:")
        lcd.move_to(0, 1)
        lcd.putstr("Input PIN:")
        if pin_buffer:
            lcd.move_to(0, 2)
            lcd.putstr("*" * len(pin_buffer))

# ==== File Utils ====
def file_exists(path):
    try:
        uos.stat(path)
        return True
    except:
        return False

def load_auth():
    try:
        with open(AUTH_CONFIG_PATH) as f:
            return json.load(f)
    except:
        return {}

def save_auth(lockers):
    with open(AUTH_CONFIG_PATH, "w") as f:
        json.dump(lockers, f)

def request_credential_sync():
    """Request latest credentials from server when online"""
    if mqtt_client:
        try:
            payload = json.dumps({"command": "sync_credentials"})
            mqtt_client.publish("locker/sync_request", payload)
            print("📤 Credential sync requested from server")
        except Exception as e:
            print("❌ Failed to request credential sync:", e)

# ==== WiFi ====
def connect_to_wifi():
    sta = network.WLAN(network.STA_IF)
    try:
        if sta.isconnected():
            sta.disconnect()
        sta.active(False)
        time.sleep(0.5)
        sta.active(True)
    except Exception as e:
        print("WiFi interface reset error:", e)
        return False

    try:
        with open(WIFI_CONFIG_PATH) as f:
            ssid = f.readline().strip()
            password = f.readline().strip()
    except Exception as e:
        print("WiFi config missing:", e)
        return False

    print("Connecting to WiFi:", ssid)
    if lcd:
        lcd.clear()
        lcd.putstr("Connecting WiFi")

    try:
        sta.connect(ssid, password)
    except:
        if lcd:
            lcd.clear()
            lcd.putstr("WiFi Connect Err")
        return False

    for _ in range(15):
        if sta.isconnected():
            ip = sta.ifconfig()[0]
            print("WiFi Connected:", ip)
            if lcd:
                lcd.clear()
                lcd.putstr(f"WiFi OK")
                lcd.move_to(0, 1)
                lcd.putstr(f"{ip}")
            buzz(1, 300)  # Success beep for WiFi connection
            time.sleep(1)
            return True
        time.sleep(1)

    print("WiFi failed")
    if lcd:
        lcd.clear()
        lcd.putstr("WiFi Failed")
    buzz(3, 200, 200)  # Error beeps for WiFi failure
    return False

def sync_time():
    ntptime.host = "129.6.15.28"
    for i in range(3):
        try:
            ntptime.settime()
            print("Time synced")
            return
        except Exception as e:
            print("NTP sync failed:", e)
            time.sleep(1)

def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=3)
    if lcd:
        lcd.clear()
        lcd.putstr("AP Mode Active")
        lcd.move_to(0, 1)
        lcd.putstr("192.168.4.1")

# ==== Locker ====
def unlock_locker(relay_pin):
    relay = RELAY_GPIO_MAP.get(relay_pin)
    if not relay:
        return
    relay.value(0)
    buzz(1, 300)  # Success beep for unlock
    if lcd:
        lcd.clear()
        lcd.putstr(f"Locker Unlocked")
    time.sleep(UNLOCK_DURATION)
    relay.value(1)
    show_default_display()
    try:
        mqtt_client.publish(MQTT_TOPIC_PUB, f"unlocked:{relay_pin}".encode())
    except:
        pass

# ==== Server Log with Offline Buffering ====
def add_history(user_id, action):
    # Try to send via MQTT if connected
    if mqtt_client:
        try:
            payload = json.dumps({
                "type": "history",
                "user_id": user_id,
                "action": action,
                "timestamp": time.time()
            })
            mqtt_client.publish(MQTT_TOPIC_PUB, payload)
            print("📤 History sent via MQTT:", payload)
            return  # Successfully sent, no need to buffer
        except Exception as e:
            print("❌ MQTT publish failed:", e)
            # Fall through to buffering

    # If MQTT not connected or publish failed, buffer the event
    print("💾 Buffering history event offline")

    try:
        # Load existing buffer
        if file_exists(HISTORY_BUFFER_PATH):
            with open(HISTORY_BUFFER_PATH, "r") as f:
                buffer = json.load(f)
        else:
            buffer = []

        # Add new event with timestamp
        buffer.append({
            "user_id": user_id,
            "action": action,
            "timestamp": time.time()
        })

        # Limit buffer size to prevent memory issues
        if len(buffer) > MAX_HISTORY_BUFFER:
            buffer = buffer[-MAX_HISTORY_BUFFER:]  # Keep last 100 events

        # Save buffer
        with open(HISTORY_BUFFER_PATH, "w") as f:
            json.dump(buffer, f)

        print(f"✅ History buffered ({len(buffer)} events pending)")

    except Exception as e:
        print(f"❌ Failed to buffer history: {e}")


def send_buffered_history():
    """Send all buffered history events when connection is restored"""
    if not mqtt_client:
        return  # Still offline

    if not file_exists(HISTORY_BUFFER_PATH):
        return  # No buffered events

    try:
        with open(HISTORY_BUFFER_PATH, "r") as f:
            buffer = json.load(f)

        if not buffer:
            return

        print(f"📤 Sending {len(buffer)} buffered history events...")

        sent_count = 0
        failed_events = []

        for event in buffer:
            try:
                payload = json.dumps({
                    "type": "history",
                    "user_id": event["user_id"],
                    "action": event["action"],
                    "timestamp": event.get("timestamp", time.time())
                })
                mqtt_client.publish(MQTT_TOPIC_PUB, payload)
                sent_count += 1
                time.sleep_ms(100)  # Small delay between sends
            except Exception as e:
                print(f"❌ Failed to send event: {e}")
                failed_events.append(event)

        # Update buffer with only failed events
        if failed_events:
            with open(HISTORY_BUFFER_PATH, "w") as f:
                json.dump(failed_events, f)
            print(f"⚠️ {len(failed_events)} events still pending")
        else:
            # All sent successfully, delete buffer file
            uos.remove(HISTORY_BUFFER_PATH)
            print(f"✅ All {sent_count} buffered events sent successfully")

    except Exception as e:
        print(f"❌ Failed to send buffered history: {e}")

# ==== RFID ====
spi = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
rdr = MFRC522(spi=spi, gpioCs=21, gpioRst=22)

def check_rfid_once():
    lockers = load_auth()
    (stat, _) = rdr.request(rdr.REQIDL)
    if stat == rdr.OK:
        (stat, raw_uid) = rdr.anticoll()
        if stat == rdr.OK:
            uid = ''.join('%02x' % b for b in raw_uid)
            print(uid)
            for user_id, locker in lockers.items():
                if locker.get("rfid") == uid and locker.get("is_active"):
                    print("✅ Matched user_id:", user_id)
                    unlock_locker(locker.get("relay_pin", 15))
                    add_history(user_id=user_id, action="Locker Unlocked by RFID")
                    return
            if lcd:
                lcd.clear()
                lcd.putstr("Access Denied")
                buzz(3, 150, 100)  # Three error beeps for access denied
                time.sleep(2)
                show_pin_entry_display()

# ==== Keypad ====
keypad = Keypad(
    keys=[["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]], 
    row_pins=[13, 12, 14, 27], col_pins=[25, 26, 33]
)

def check_keypad_once():
    global pin_buffer, failed_pin_attempts, current_display
    if is_system_locked():
        if current_display != "locked":
            if lcd:
                lcd.clear()
                lcd.putstr("Keypad is locked")
            current_display = "locked"
        time.sleep(0.1)
        return

    if current_display != "default":
        if lcd:
            lcd.clear()
            lcd.putstr("Scan RFID:")
            lcd.move_to(0, 1)
            lcd.putstr("Input PIN:")
        current_display = "default"

    lockers = load_auth()
    key = keypad.get_key()
    if key and key not in ['*', '#']:
        pin_buffer += key
        buzz(1, 30)  # Short beep for key press feedback
        print(f"Entered PIN: {pin_buffer}") 
        if lcd:
            lcd.move_to(0, 2)
            lcd.putstr("*" * len(pin_buffer))

        if len(pin_buffer) == 4:
            for user_id, locker in lockers.items():
                if locker.get("pin") == pin_buffer and locker.get("is_active"):
                    unlock_locker(locker.get("relay_pin", 15))
                    add_history(user_id=user_id, action="Locker Unlocked by PIN")
                    pin_buffer = ""
                    failed_pin_attempts = 0
                    show_default_display()
                    return
            record_pin_failure()
            pin_buffer = ""
            show_pin_entry_display()

# ==== MQTT ====
def connect_mqtt():
    global mqtt_client
    def sub_cb(topic, msg):
        print("📩 MQTT:", topic, msg)

        try:
            payload = msg.decode()
            config = json.loads(payload)

            # Handle reset lockout command
            if config.get("command") == "reset_lockout":
                print("🔓 Received lockout reset command")
                reset_lockout()
                if mqtt_client:
                    mqtt_client.publish(MQTT_TOPIC_PUB, json.dumps({
                        "type": "lockout_reset",
                        "message": "Lockout has been reset",
                        "timestamp": time.time()
                    }))
                return

            # Check if system is locked for other commands
            if is_system_locked() and config.get("command") != "reset_lockout":
                remaining = int(locked_until_time - time.time())
                print("⛔ System is locked. Remaining: {}s".format(remaining))
                try:
                    if mqtt_client:
                        mqtt_client.publish(MQTT_TOPIC_PUB, json.dumps({
                            "type": "lock_alert",
                            "message": "MQTT command rejected due to system lock",
                            "remaining": remaining
                        }))
                        print("📤 MQTT: Lock alert sent")
                except Exception as e:
                    print("❌ MQTT lock alert failed:", e)
                return

            lockers = load_auth()
            print(payload)

            if topic == MQTT_TOPIC_VALIDATE_PIN or topic == MQTT_TOPIC_LOCKDOWN:
                handle_pin_validation(payload)

            elif config.get("command") == "unlock" and "user_id" in config:
                user_id = str(config["user_id"])
                if user_id in lockers:
                    locker = lockers[user_id]
                    if locker.get("is_active") and str(locker.get('rfid')):
                        unlock_locker(locker.get("relay_pin", 15))
                        print(f"✅ Unlocked locker for user {user_id}")
                    else:
                        print(f"❌ User {user_id}'s locker is not valid")
                else:
                    print(f"❌ Locker config not found for user {user_id}")

            elif config.get("type") == "credential_update" and "user_id" in config:
                # Handle single user credential update
                user_id = str(config["user_id"])
                new_data = {
                    "pin": config.get("pin"),
                    "rfid": config.get("rfid"),
                    "relay_pin": config.get("relay_pin", 15),
                    "is_active": config.get("is_active", True),
                    "updated_at": time.time()
                }
                lockers[user_id] = new_data
                save_auth(lockers)
                print(f"✅ Credentials updated for user {user_id}: PIN={config.get('pin')}, RFID={config.get('rfid')}")

                # Send acknowledgment
                if mqtt_client:
                    mqtt_client.publish(MQTT_TOPIC_PUB, json.dumps({
                        "type": "credential_update_ack",
                        "user_id": user_id,
                        "timestamp": time.time()
                    }))

            elif config.get("type") == "credential_sync" and "credentials" in config:
                # Handle full credential sync from server
                print("📥 Receiving full credential sync from server")
                lockers.clear()
                for cred in config["credentials"]:
                    user_id = str(cred["user_id"])
                    lockers[user_id] = {
                        "pin": cred.get("pin"),
                        "rfid": cred.get("rfid"),
                        "relay_pin": cred.get("relay_pin", 15),
                        "is_active": cred.get("is_active", True),
                        "updated_at": time.time()
                    }
                save_auth(lockers)
                print(f"✅ Synced {len(lockers)} user credentials from server")

            elif "user_id" in config and "pin" in config and "rfid" in config:
                # Legacy format support
                user_id = str(config["user_id"])
                new_data = {
                    "pin": config["pin"],
                    "rfid": config["rfid"],
                    "relay_pin": config.get("relay_pin", 15),
                    "is_active": config.get("is_active", True),
                    "updated_at": time.time()
                }
                lockers[user_id] = new_data
                save_auth(lockers)
                print(f"✅ Config saved/updated for user {user_id}")

            elif "delete" in config and "user_id" in config:
                user_id = str(config["user_id"])
                if user_id in lockers:
                    del lockers[user_id]
                    save_auth(lockers)
                    print(f"🗑️ Deleted locker for user {user_id}")
                else:
                    print(f"❌ No config found to delete for user {user_id}")

        except Exception as e:
            print("❌ MQTT error:", e)

    try:
        if lcd:
            lcd.clear()
            lcd.putstr("Connecting MQTT...")

        print("Connecting to MQTT broker...")
        mqtt_client = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_BROKER, port=MQTT_PORT,
                                 user=MQTT_USERNAME, password=MQTT_PASSWORD, ssl=True,
                                 ssl_params={"server_hostname": MQTT_BROKER}, keepalive=60)
        mqtt_client.set_callback(sub_cb)

        # Connect with timeout protection
        mqtt_client.connect()
        time.sleep_ms(500)  # Give connection time to establish

        mqtt_client.subscribe(MQTT_TOPIC_SUB)
        mqtt_client.subscribe(MQTT_TOPIC_VALIDATE_PIN)
        mqtt_client.subscribe(MQTT_TOPIC_LOCKDOWN)
        mqtt_client.subscribe(b"locker/sync_response")

        if lcd:
            lcd.clear()
            lcd.putstr("MQTT Connected")
            buzz(2, 100, 100)  # Two quick beeps for MQTT connection
            time.sleep(1)
            lcd.clear()
            lcd.putstr("Syncing credentials...")
        print("✅ MQTT connected")

        # Request credential sync on connect
        request_credential_sync()

        # Send any buffered history from offline period
        send_buffered_history()

        time.sleep(2)
        show_default_display()
    except Exception as e:
        print("MQTT connect failed:", e)
        if lcd:
            lcd.clear()
            lcd.putstr("MQTT Failed")
            time.sleep(1)
        mqtt_client = None

# ==== Unified Loop ====
def unified_loop():
    global mqtt_client
    retry = 0
    last_ping = time.time()
    while True:
        try:
            check_rfid_once()
            check_keypad_once()

            if not network.WLAN(network.STA_IF).isconnected():
                connect_to_wifi()
                sync_time()

            if mqtt_client:
                try:
                    mqtt_client.check_msg()
                    if time.time() - last_ping > 20:
                        mqtt_client.ping()
                        last_ping = time.time()
                except Exception as e:
                    print("MQTT disconnected:", e)
                    mqtt_client = None
                    retry = 0

            if not mqtt_client:
                retry += 1
                if retry >= 20:  # Wait 2 seconds before retry (20 * 0.1s)
                    print("🔁 Reconnecting MQTT...")
                    connect_mqtt()
                    retry = 0

            gc.collect()
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Loop error: {e}")
            time.sleep(1)  # Brief pause before continuing

# ==== Microdot Web Config ====
app = Microdot()
Response.default_content_type = 'application/json'

@app.route('/')
def index(req):
    return Response(body="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 WiFi Setup</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f2f2f2;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background: #fff;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 90%;
        }
        h2 {
            text-align: center;
            margin-bottom: 1.2rem;
        }
        label {
            display: block;
            margin-top: 1rem;
            margin-bottom: 0.3rem;
            font-weight: bold;
        }
        input {
            width: 100%;
            padding: 0.6rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            margin-top: 1.5rem;
            width: 100%;
            padding: 0.75rem;
            font-size: 1rem;
            background: #007bff;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>WiFi Setup</h2>
        <form action="/configure" method="post">
            <label for="ssid">SSID:</label>
            <input type="text" id="ssid" name="ssid" required>

            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>

            <button type="submit">Save</button>
        </form>
    </div>
</body>
</html>
""", headers={'Content-Type': 'text/html'})

@app.route('/configure', methods=['POST'])
def configure(req):
    ssid = req.form['ssid']
    password = req.form['password']
    with open(WIFI_CONFIG_PATH, "w") as f:
        f.write(f"{ssid}\n{password}")
    time.sleep(2)
    machine.reset()
    return {"status": "restarting"}

@app.route('/unlock', methods=['POST'])
def unlock(req):
    try:
        relay_pin = int(req.json.get("relay_pin"))
        unlock_locker(relay_pin)
        return {"status": "ok"}
    except:
        return {"status": "error"}

@app.route('/reset_lockout', methods=['POST'])
def web_reset_lockout(req):
    try:
        reset_lockout()
        return {"status": "lockout_reset", "message": "System lockout has been reset"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==== Start ====
print("=== BOOT SEQUENCE START ===")

# Try WiFi connection
wifi_connected = connect_to_wifi()

if wifi_connected:
    print("WiFi connected, syncing time...")
    try:
        sync_time()
    except Exception as e:
        print("Time sync failed:", e)

    # Try MQTT but don't block if it fails
    print("Attempting MQTT connection...")
    try:
        connect_mqtt()
    except Exception as e:
        print("MQTT failed during boot:", e)
        if lcd:
            lcd.clear()
            lcd.putstr("MQTT Failed")
            lcd.move_to(0, 1)
            lcd.putstr("Continuing...")
            time.sleep(2)
else:
    print("WiFi failed, starting AP mode...")
    start_ap()

# Always show default display and start main loop
print("Starting main operations...")
show_default_display()

# Start unified loop in background thread
print("Starting unified loop thread...")
_thread.start_new_thread(unified_loop, ())

# Start web server (this blocks, must be last)
print("Starting web server on port 80...")
try:
    app.run(port=80)
except Exception as e:
    print("Web server error:", e)
    # If web server fails, keep system running with just the loop
    while True:
        time.sleep(1)
