from machine import Pin, SPI, I2C
import network, time, uos, json, _thread
from microdot import Microdot, Response
from mfrc522 import MFRC522
import machine, gc, ntptime
from keypad_matrix import Keypad
from umqtt.simple import MQTTClient
from i2c_lcd import I2cLcd


# ==== Configuration ====
RELAY_GPIO_MAP = {15: Pin(15, Pin.OUT), 4: Pin(4, Pin.OUT)}
UNLOCK_DURATION = 3
AP_SSID = "ESP32-Config"
AP_PASSWORD = "12345678"
WIFI_CONFIG_PATH = "wifi_config.txt"
AUTH_CONFIG_PATH = "auth_config.json"
MQTT_BROKER = "a26bb47bf62f46468d153a09fbffa641.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "esp32_locker_1"
MQTT_USERNAME = "rikumqtt"
MQTT_PASSWORD = "@Riku01234"
MQTT_TOPIC_SUB = b"locker/control"
MQTT_TOPIC_PUB = b"locker/status"
mqtt_client = None
pin_buffer = ""
SERVER_URL = "https://locker-system.up.railway.app"

LOCK_DURATION = 2 * 60
MAX_FAILED_ATTEMPTS = 3
failed_pin_attempts = 0
locked_until_time = 0

# ==== LCD Setup ====
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
lcd = None
try:
    lcd_addr = i2c.scan()[0]
    lcd = I2cLcd(i2c, lcd_addr, 4, 20)
    lcd.clear()
    lcd.putstr("Input Pin:")
except:
    print("LCD init failed")

for relay in RELAY_GPIO_MAP.values():
    relay.value(1)

# ==== Lock Function for Failed Attempts ====
def is_system_locked():
    return time.time() < locked_until_time

def record_pin_failure():
    global failed_pin_attempts, locked_until_time
    failed_pin_attempts += 1
    remaining = MAX_FAILED_ATTEMPTS - failed_pin_attempts

    if failed_pin_attempts >= MAX_FAILED_ATTEMPTS:
        locked_until_time = time.time() + LOCK_DURATION
        failed_pin_attempts = 0
        print(f"🔒 System locked for {LOCK_DURATION // 60} mins due to too many PIN failures.")
        _thread.start_new_thread(show_lockout_timer, ())
    else:
        print(f"❌ Wrong PIN. {remaining} attempts left.")
        lcd.clear(); lcd.putstr(f"Wrong PIN\nAttempts Left: {remaining}")
        
def show_lockout_timer():
    global locked_until_time
    while is_system_locked():
        remaining = int(locked_until_time - time.time())
        lcd.clear()
        lcd.putstr("System Locked!\nRetry in: {}s".format(remaining))
        time.sleep(1)

    lcd.clear()
    lcd.putstr("Input Pin:")

# ==== File Utils ====
def file_exists(path):
    try: uos.stat(path); return True
    except: return False

def load_auth():
    try:
        with open(AUTH_CONFIG_PATH) as f:
            return json.load(f)
    except:
        return {}

def save_auth(lockers):
    with open(AUTH_CONFIG_PATH, "w") as f:
        json.dump(lockers, f)

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
    lcd.clear(); lcd.putstr("Connecting WiFi")
    try:
        sta.connect(ssid, password)
    except:
        lcd.clear(); lcd.putstr("WiFi Connect Err")
        return False

    for _ in range(15):
        if sta.isconnected():
            ip = sta.ifconfig()[0]
            print("WiFi Connected:", ip)
            lcd.clear(); lcd.putstr(f"Connected:\n{ip}")
            return True
        time.sleep(1)

    print("WiFi failed")
    lcd.clear(); lcd.putstr("WiFi Failed")
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
    lcd.clear(); lcd.putstr("AP Mode Active \n192.168.4.1")
    


# ==== Locker ====
def unlock_locker(relay_pin):
    relay = RELAY_GPIO_MAP.get(relay_pin)
    if not relay: return
    relay.value(0)
    lcd.clear(); lcd.putstr(f"Unlocked Locker")
    time.sleep(UNLOCK_DURATION)
    relay.value(1)
    lcd.clear(); lcd.putstr("Input Pin:")
    try:
        mqtt_client.publish(MQTT_TOPIC_PUB, f"unlocked:{relay_pin}".encode())
    except: pass
    

# ==== Server Log ====
def add_history(user_id, action):
    import ujson
    if mqtt_client:
        try:
            payload = ujson.dumps({
                "type": "history",
                "user_id": user_id,
                "action": action
            })
            mqtt_client.publish(MQTT_TOPIC_PUB, payload)
            print("📤 History sent via MQTT:", payload)
        except Exception as e:
            print("❌ MQTT publish failed:", e)
    else:
        print("⚠️ MQTT not connected")


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
            lcd.clear(); lcd.putstr("Access Denied")
            
# ==== Keypad ====
keypad = Keypad(
    keys=[["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]],
    row_pins=[13, 12, 14, 27], col_pins=[26, 25, 33]
)

def check_keypad_once():
    global pin_buffer, failed_pin_attempts

    if is_system_locked():
        print("⛔ Keypad access is locked.")
        time.sleep(1)
        return

    lockers = load_auth()
    key = keypad.get_key()
    if key and key not in ['*', '#']:
        pin_buffer += key
        lcd.move_to(0, 1); lcd.putstr("*" * len(pin_buffer))

        if len(pin_buffer) == 4:
            for user_id, locker in lockers.items():
                if locker.get("pin") == pin_buffer and locker.get("is_active"):
                    unlock_locker(locker.get("relay_pin", 15))
                    add_history(user_id=user_id, action="Locker Unlocked by PIN")
                    pin_buffer = ""
                    failed_pin_attempts = 0  # ✅ reset on success
                    return

            record_pin_failure()
            time.sleep(2)
            pin_buffer = ""
            lcd.clear(); lcd.putstr("Input Pin:")

# ==== MQTT ====
def connect_mqtt():
    global mqtt_client

    def sub_cb(topic, msg):
        print("📩 MQTT:", topic, msg)

        if is_system_locked():
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

        try:
            payload = msg.decode()
            config = json.loads(payload)
            lockers = load_auth()

            # ==== Unlock Command ====
            if config.get("command") == "unlock" and "user_id" in config:
                user_id = str(config["user_id"])
                if user_id in lockers:
                    locker = lockers[user_id]
                    if locker.get("is_active") and str(locker.get('rfid')):
                        relay_pin = locker.get("relay_pin", 15)
                        unlock_locker(relay_pin)
                        print(f"✅ Unlocked locker for user {user_id}")
                    else:
                        print(f"❌ User {user_id}'s locker is not valid")
                else:
                    print(f"❌ Locker config not found for user {user_id}")

            # ==== Config Save/Update ====
            elif "user_id" in config and "pin" in config and "rfid" in config:
                user_id = str(config["user_id"])
                new_data = {
                    "pin": config["pin"],
                    "rfid": config["rfid"],
                    "relay_pin": config.get("relay_pin", 15),
                    "is_active": config.get("is_active", True)
                }
                lockers[user_id] = new_data
                save_auth(lockers)
                print(f"✅ Config saved/updated for user {user_id}")

            # ==== Delete ====
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

    # ==== MQTT Client Init ====
    try:
        mqtt_client = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_BROKER, port=MQTT_PORT,
                                 user=MQTT_USERNAME, password=MQTT_PASSWORD, ssl=True,
                                 ssl_params={"server_hostname": MQTT_BROKER}, keepalive=60)
        mqtt_client.set_callback(sub_cb)
        mqtt_client.connect()
        mqtt_client.subscribe(MQTT_TOPIC_SUB)
        lcd.clear()
        lcd.putstr("MQTT Connected")
        print("✅ MQTT connected")
    except Exception as e:
        print("MQTT connect failed:", e)
        mqtt_client = None


# ==== Unified Loop ====
def unified_loop():
    global mqtt_client
    retry = 0
    last_ping = time.time()

    while True:
        check_rfid_once()
        check_keypad_once()

        if not network.WLAN(network.STA_IF).isconnected():
            connect_to_wifi(); sync_time()

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
            if retry >= 2:
                print("🔁 Reconnecting MQTT...")
                connect_mqtt()
                retry = 0

        gc.collect()
        time.sleep(0.1)

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

# ==== Start ====
if connect_to_wifi():
    sync_time(); connect_mqtt()
else:
    start_ap()

_thread.start_new_thread(unified_loop, ())
app.run(port=80)

