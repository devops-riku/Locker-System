# mqtt.py
import json
import paho.mqtt.client as mqtt
import time

from app.services.history_logs import log_history

MQTT_BROKER = "a26bb47bf62f46468d153a09fbffa641.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "rikumqtt"
MQTT_PASSWORD = "@Riku01234"
MQTT_TOPIC = "locker/control"
MQTT_TOPIC_PUB = "locker/status"

mqtt_client = mqtt.Client()

# Apply TLS and auth only once
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT connected to HiveMQ.")
        client.subscribe(MQTT_TOPIC_PUB)
        print(f"📡 Subscribed to {MQTT_TOPIC_PUB}")
    else:
        print(f"⚠️ MQTT connect failed with code {rc}")

def on_disconnect(client, userdata, rc):
    print("🔌 MQTT disconnected. Reconnecting in 5s...")
    time.sleep(5)
    reconnect_mqtt()

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📥 Message received on {msg.topic}: {payload}")

        if payload.get("type") == "history":
            user_id = payload.get("user_id")
            action = payload.get("action")

            log_history(user_id=int(user_id), action=action)


    except Exception as e:
        print("❌ Failed to handle message:", e)

def reconnect_mqtt():
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
            mqtt_client.loop_start()
            break
        except Exception as e:
            print("❌ Reconnect failed:", e)
            time.sleep(5)

def mqtt_setup():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    reconnect_mqtt()