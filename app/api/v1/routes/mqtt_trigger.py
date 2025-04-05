
import json
import os
import time
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv
from app.models.schemas import HistoryLogRequest
from app.services.admin_service import get_user_by_id, get_user_locker_info, get_user_session
from app.services.history_logs import log_history
from app.services.mqtt import mqtt_client
load_dotenv()

router = APIRouter()



@router.post("/unlock-locker")
async def unlock_locker(request: Request, history: HistoryLogRequest):
    user_id = get_user_session(request).get('id')

    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT not connected")

    locker_info = get_user_locker_info(user_id)
    if not locker_info or "relay_pin" not in locker_info[0]:
        raise HTTPException(status_code=404, detail="No assigned locker found for user")

    # Publish locker_id instead of raw relay_pin
    mqtt_payload = {
        "user_id": str(user_id),
        "rfid": locker_info[0]["rfid_serial_number"],
        "command": "unlock"
    }

    try:
        mqtt_client.publish("locker/control", json.dumps(mqtt_payload))
        print(f"🔓 Published to MQTT: {mqtt_payload}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT publish failed: {e}")

    log_history(user_id=user_id, action=history.action)

    return {"message": "Unlock command sent successfully"}

