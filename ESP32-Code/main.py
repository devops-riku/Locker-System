from machine import Pin, SPI
import network, time, uos, json, _thread
from microdot import Microdot, Response
from mfrc522 import MFRC522
import urequests
import machine
import os

from keypad_matrix import Keypad
from umqtt.simple import MQTTClient

# Configuration
RELAY_PIN = 15
UNLOCK_DURATION = 3
AP_SSID = "ESP32-Config"
AP_PASSWORD = "12345678"
WIFI_CONFIG_PATH = "wifi_config.txt"
AUTH_CONFIG_PATH = "auth_config.json"
SERVER_URL = "http://your-web-server.com/api/credentials"

# MQTT Config
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "esp32_locker_1"
MQTT_TOPIC_SUB = b"locker/control"
MQTT_TOPIC_PUB = b"locker/status"
mqtt_client = None

# Globals
authorized_pin = ""
authorized_rfid = ""
pin_buffer = ""
last_update_time = time.time()

# File checker
def file_exists(path):
    try:
        os.stat(path)
        return True
    except:
        return False

# Load saved PIN + RFID
def load_auth():
    global authorized_pin, authorized_rfid
    try:
        with open(AUTH_CONFIG_PATH) as f:
            data = json.load(f)
            authorized_pin = data.get("pin", "")
            authorized_rfid = data.get("rfid", "")
            print("Loaded PIN:", authorized_pin, "RFID:", authorized_rfid)
    except:
        print("No local auth config")

# Save PIN/RFID
def save_auth(pin=None, rfid=None):
    if file_exists(AUTH_CONFIG_PATH):
        with open(AUTH_CONFIG_PATH, "r") as f:
            data = json.load(f)
    else:
        data = {}

    if pin is not None:
        data["pin"] = pin
    if rfid is not None:
        data["rfid"] = rfid

    with open(AUTH_CONFIG_PATH, "w") as f:
        json.dump(data, f)

# Connect WiFi
def connect_to_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    try:
        with open(WIFI_CONFIG_PATH) as f:
            ssid = f.readline().strip()
            password = f.readline().strip()

        print(f"Connecting to WiFi SSID: {ssid}")
        sta.connect(str(ssid), str(password))

        timeout = 10
        for _ in range(timeout * 2):
            if sta.isconnected():
                print("✅ WiFi Connected:", sta.ifconfig()[0])
                return True
            time.sleep(0.5)

        print("❌ Failed to connect within timeout.")
    except Exception as e:
        print("⚠️ WiFi Internal Error:", e)

    return False

# Access Point fallback
def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    print("Access Point IP:", ap.ifconfig()[0])

# Fetch from server
def fetch_credentials():
    try:
        r = urequests.get(SERVER_URL)
        if r.status_code == 200:
            data = r.json()
            global authorized_pin, authorized_rfid
            if data.get("pin") and data.get("rfid"):
                if data["pin"] != authorized_pin or data["rfid"] != authorized_rfid:
                    authorized_pin = data["pin"]
                    authorized_rfid = data["rfid"]
                    save_auth()
                    print("Updated credentials from server")
        r.close()
    except Exception as e:
        print("Failed to fetch credentials:", e)

# Unlock relay
def unlock_locker():
    print("ACCESS GRANTED - Unlocking locker")
    relay.value(0)
    time.sleep(UNLOCK_DURATION)
    relay.value(1)
    print("Locker relocked")

    try:
        mqtt_client.publish(MQTT_TOPIC_PUB, b"unlocked")
    except:
        print("⚠️ MQTT publish failed")

# RFID check
def check_rfid():
    while True:
        (stat, _) = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            (stat, raw_uid) = rdr.anticoll()
            if stat == rdr.OK:
                uid = ''.join('%02x' % b for b in raw_uid)
                print("RFID:", uid)
                if uid == authorized_rfid:
                    unlock_locker()
                else:
                    print("ACCESS DENIED - Invalid RFID")
        time.sleep(0.5)

# Keypad check
def check_keypad():
    global pin_buffer
    while True:
        key = keypad.get_key()
        if key:
            if key in ['*', '#']:
                print("Invalid key")
                continue
            pin_buffer += key
            print("*", end="")
            if len(pin_buffer) == 4:
                print("\nPIN entered:", pin_buffer)
                if pin_buffer == authorized_pin:
                    unlock_locker()
                else:
                    print("ACCESS DENIED - Wrong PIN")
                pin_buffer = ""
        time.sleep(0.1)

# MQTT connection
def connect_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
    
    def sub_cb(topic, msg):
        print("📩 MQTT Message:", topic, msg)
        if topic == MQTT_TOPIC_SUB:
            if msg == b"unlock":
                unlock_locker()
    
    mqtt_client.set_callback(sub_cb)
    mqtt_client.connect()
    mqtt_client.subscribe(MQTT_TOPIC_SUB)
    print("✅ MQTT connected and subscribed to", MQTT_TOPIC_SUB)

# MQTT loop
def mqtt_loop():
    while True:
        try:
            mqtt_client.check_msg()
        except Exception as e:
            print("❌ MQTT error:", e)
        time.sleep(1)

# Hardware
relay = Pin(RELAY_PIN, Pin.OUT)
relay.value(1)

spi = SPI(1, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(23), miso=Pin(19))
rdr = MFRC522(spi=spi, gpioCs=21, gpioRst=22)

keypad = Keypad(
    keys=[['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['*', '0', '#']],
    row_pins=[13, 12, 14, 27],
    col_pins=[26, 25, 33]
)

# Web server
app = Microdot()
Response.default_content_type = 'application/json'

@app.route('/')
def index(req):
    return Response(body="""<html>
    <head><title>ESP32 Setup</title></head>
    <body>
        <h2>ESP32 WiFi + PIN + Serial Setup</h2>
        <form action="/configure" method="post">
            <label>WiFi SSID:</label><br>
            <input type="text" name="ssid"><br><br>
            <label>WiFi Password:</label><br>
            <input type="password" name="password"><br><br>
            <label>Locker PIN (4 digits):</label><br>
            <input type="text" name="pin" maxlength="4"><br><br>
            <label>RFID Serial:</label><br>
            <input type="text" name="rfid"><br><br>
            <button type="submit">Save</button>
        </form>
    </body>
    </html>""", headers={'Content-Type': 'text/html'})


@app.route('/configure', methods=['POST'])
def configure(req):
    ssid = req.form["ssid"]
    password = req.form["password"]
    pin = req.form["pin"]
    rfid = req.form["rfid"]

    with open(WIFI_CONFIG_PATH, "w") as f:
        f.write(f"{ssid}\n{password}")

    save_auth(pin=pin, rfid=rfid)

    time.sleep(2)
    machine.reset()

    return Response("Rebooting...", headers={'Content-Type': 'text/plain'})


@app.route('/unlock', methods=['POST'])
def unlock(req):
    unlock_locker()
    return {"status": "success", "message": "Locker unlocked"}

# Init
if connect_to_wifi():
    fetch_credentials()
    connect_mqtt()
else:
    start_ap()

load_auth()

_thread.start_new_thread(check_rfid, ())
_thread.start_new_thread(check_keypad, ())
_thread.start_new_thread(mqtt_loop, ())
app.run(port=80)
