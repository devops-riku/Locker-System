# mqtt.py
import json
from fastapi import HTTPException
import paho.mqtt.client as mqtt
import time

from app.models.models import UserCredential
from app.services.history_logs import log_history
from app.models.database import *

MQTT_BROKER = "a26bb47bf62f46468d153a09fbffa641.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "rikumqtt"
MQTT_PASSWORD = "@Riku01234"
MQTT_TOPIC = "locker/control"
MQTT_TOPIC_PUB = "locker/status"
MQTT_TOPIC_VALIDATE_PIN = "locker/validate_pin"

mqtt_client = mqtt.Client()

# Apply TLS and auth only once
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT connected to HiveMQ.")
        client.subscribe(MQTT_TOPIC_PUB)
        client.subscribe(MQTT_TOPIC_VALIDATE_PIN)
        print(f"📡 Subscribed to {MQTT_TOPIC_PUB} and {MQTT_TOPIC_VALIDATE_PIN}")
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

        if msg.topic == MQTT_TOPIC_VALIDATE_PIN:
            handle_pin_validation(payload)
        elif payload.get("type") == "history":
            user_id = payload.get("user_id")
            action = payload.get("action")
            log_history(user_id=int(user_id), action=action)

    except Exception as e:
        print("❌ Failed to handle message:", e)

def handle_pin_validation(payload):
    user_id = payload.get("user_id")
    lock_duration = payload.get("duration")
    try:
        # Query the database for the user's credentials
        user_credentials = db_session.query(UserCredential).filter_by(user_id=user_id).first()
        user_credentials.attempt_duration = lock_duration
        db_session.commit()
        
        # If no credentials are found, raise an HTTPException
        if not user_credentials:
            raise HTTPException(status_code=404, detail="User credentials not found")
        
        return user_credentials
        
    except Exception as e:
        db_session.rollback()
        raise e


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