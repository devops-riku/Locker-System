# mqtt.py
import json
from fastapi import HTTPException
import paho.mqtt.client as mqtt
import time

from app.models.models import UserCredential
from app.services.history_logs import log_history
from app.models.database import *
from datetime import datetime, timedelta

MQTT_BROKER = "a26bb47bf62f46468d153a09fbffa641.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "rikumqtt"
MQTT_PASSWORD = "@Riku01234"
MQTT_TOPIC = "locker/control"
MQTT_TOPIC_PUB = "locker/status"
MQTT_TOPIC_VALIDATE_PIN = "locker/validate_pin"
MQTT_TOPIC_LOCKDOWN = "locker/lockdown"

# Global lockdown state
global_lockdown = {
    "is_locked": False,
    "end_time": None,
    "source": None,
    "user_id": None
}

mqtt_client = mqtt.Client()

# Apply TLS and auth only once
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT connected to HiveMQ.")
        client.subscribe(MQTT_TOPIC_PUB)
        client.subscribe(MQTT_TOPIC_VALIDATE_PIN)
        client.subscribe(MQTT_TOPIC_LOCKDOWN)
        client.subscribe("locker/sync_request")
        print(f"📡 Subscribed to {MQTT_TOPIC_PUB}, {MQTT_TOPIC_VALIDATE_PIN}, {MQTT_TOPIC_LOCKDOWN}, and locker/sync_request")
    else:
        print(f"⚠️ MQTT connect failed with code {rc}")

def on_disconnect(client, userdata, rc):
    print("🔌 MQTT disconnected. Reconnecting in 5s...")
    time.sleep(5)
    reconnect_mqtt()

def on_message(client, userdata, msg):
    global global_lockdown
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📥 Message received on {msg.topic}: {payload}")

        if msg.topic == MQTT_TOPIC_VALIDATE_PIN:
            handle_pin_validation(payload)
        elif msg.topic == MQTT_TOPIC_LOCKDOWN:
            handle_hardware_lockdown(payload)
        elif msg.topic == "locker/sync_request":
            # Handle credential sync request from ESP32
            handle_credential_sync_request(payload)
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

def handle_hardware_lockdown(payload):
    """Handle lockdown notifications from hardware"""
    global global_lockdown
    try:
        payload_type = payload.get("type")
        if payload_type == "hardware_lockdown":
            user_id = payload.get("user_id")
            lockout_seconds = payload.get("lockout_seconds", 120)
            end_time = datetime.now() + timedelta(seconds=lockout_seconds)

            # Update global lockdown state
            global_lockdown["is_locked"] = True
            global_lockdown["end_time"] = end_time
            global_lockdown["source"] = "hardware"
            global_lockdown["user_id"] = user_id

            print(f"🔒 Hardware lockdown activated for user {user_id}, ending at {end_time}")

            # Update database for the user
            try:
                user_credentials = db_session.query(UserCredential).filter_by(user_id=user_id).first()
                if user_credentials:
                    user_credentials.attempt_duration = end_time
                    db_session.commit()
                    print(f"✅ Database updated for user {user_id} lockdown")
                else:
                    print(f"❌ User credentials not found for user {user_id}")
            except Exception as db_error:
                db_session.rollback()
                print(f"❌ Database update failed: {db_error}")

    except Exception as e:
        print(f"❌ Error handling hardware lockdown: {e}")

def is_globally_locked():
    """Check if the system is globally locked"""
    global global_lockdown
    if not global_lockdown["is_locked"]:
        return False

    if global_lockdown["end_time"] and datetime.now() < global_lockdown["end_time"]:
        return True
    else:
        # Lockdown expired, clear it
        global_lockdown["is_locked"] = False
        global_lockdown["end_time"] = None
        global_lockdown["source"] = None
        global_lockdown["user_id"] = None
        return False

def get_lockdown_status():
    """Get current lockdown status with remaining time"""
    global global_lockdown
    if not is_globally_locked():
        return {"is_locked": False}

    remaining_seconds = int((global_lockdown["end_time"] - datetime.now()).total_seconds())
    return {
        "is_locked": True,
        "remaining_seconds": max(0, remaining_seconds),
        "end_time": global_lockdown["end_time"].isoformat(),
        "source": global_lockdown["source"],
        "user_id": global_lockdown["user_id"]
    }

def set_web_lockdown(user_id, duration_seconds=120):
    """Set lockdown from web interface"""
    global global_lockdown
    end_time = datetime.now() + timedelta(seconds=duration_seconds)

    global_lockdown["is_locked"] = True
    global_lockdown["end_time"] = end_time
    global_lockdown["source"] = "web"
    global_lockdown["user_id"] = user_id

    # Send MQTT message to hardware
    payload = {
        "type": "web_lockdown",
        "user_id": user_id,
        "lockout_duration": duration_seconds,
        "source": "web",
        "end_time": time.mktime(end_time.timetuple()),
        "message": f"System locked from web for {duration_seconds} seconds"
    }

    try:
        mqtt_client.publish(MQTT_TOPIC_LOCKDOWN, json.dumps(payload))
        print(f"📤 Web lockdown sent to hardware: {payload}")
    except Exception as e:
        print(f"❌ Failed to send web lockdown to hardware: {e}")

def handle_credential_sync_request(payload):
    """Send all active user credentials to ESP32"""
    try:
        # Get all active user credentials from database
        from app.models.models import User
        active_users = db_session.query(User).filter(User.is_active == True).all()

        credentials = []
        for user in active_users:
            if user.credentials:
                for cred in user.credentials:
                    if cred.is_active and cred.locker:
                        credentials.append({
                            "user_id": user.id,
                            "pin": cred.pin_number,
                            "rfid": cred.rfid_serial_number or "",
                            "relay_pin": cred.locker.relay_pin,
                            "is_active": cred.is_active
                        })

        sync_payload = {
            "type": "credential_sync",
            "credentials": credentials,
            "timestamp": time.time()
        }

        mqtt_client.publish("locker/sync_response", json.dumps(sync_payload))
        print(f"📤 Sent {len(credentials)} credentials to ESP32")

    except Exception as e:
        print(f"❌ Failed to sync credentials: {e}")

def publish_credential_update(user_id, pin, rfid, relay_pin, is_active=True):
    """Publish credential update for a single user to ESP32"""
    try:
        payload = {
            "type": "credential_update",
            "user_id": user_id,
            "pin": pin,
            "rfid": rfid or "",
            "relay_pin": relay_pin,
            "is_active": is_active,
            "timestamp": time.time()
        }

        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
        print(f"📤 Credential update sent for user {user_id}")

    except Exception as e:
        print(f"❌ Failed to publish credential update: {e}")

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

def get_mqtt_client():
    """Get the MQTT client instance"""
    return mqtt_client