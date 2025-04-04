
import os
import time
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv
from app.models.schemas import HistoryLogRequest
from app.services.admin_service import get_user_session
from app.services.history_logs import log_history
from app.services.mqtt import mqtt_client
load_dotenv()

router = APIRouter()





@router.post("/unlock-locker")
async def unlock_locker(request: Request, history: HistoryLogRequest):
    if mqtt_client.is_connected():
            mqtt_client.publish("locker/control", "unlock")
    else:
         raise HTTPException(status_code=503, detail="MQTT not connected")
    log_history(user_id=get_user_session(request).get('id'), action=history.action)
    return {"message": "Locker unlocked successfully"}




@router.post("/unlock")
def hive_unlock():
    try:
        if mqtt_client.is_connected():
            mqtt_client.publish("locker/control", "unlock")
            return {"status": "ok", "message": "MQTT 'unlock' sent to locker"}
        else:
            raise HTTPException(status_code=503, detail="MQTT not connected")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))