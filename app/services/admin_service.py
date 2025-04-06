import inspect
import json

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from app.models.database import *
from app.models.models import *
from sqlalchemy.orm import *
from app.services.mqtt import mqtt_client
import os
load_dotenv()

def get_user_session(request):
    if request.session.get('user'):
        return request.session['user']
    return None


def user_is_logged_in(request) -> bool:
    """Mock function to check if a user is logged in"""
    return request.session.get("user", False)


def check_super_admin() -> bool:
    """Check if there is any super admin user in the User model"""
    try:
        super_admin_exists = db_session.query(User).filter_by(is_super_admin=True).first() is not None
        return super_admin_exists
    except Exception as e:
        db_session.rollback()
        raise e

async def is_super_admin(request: Request) -> bool:
    user_session = get_user_session(request)
    if not user_session.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Access forbidden: Super admin only")
    return True


def CreateUser(first_name=None, last_name=None, id_number=None, address=None, email=None, locker_number=None, rfid_serial_number=None, pin_number=None, created_by=None, is_super_admin=False):
    try:

        get_locker_by_id = db_session.query(Locker).filter_by(id=locker_number).first()
        user = User(first_name=first_name, last_name=last_name, id_number=id_number, address=address, email=email, created_by=created_by, is_super_admin=is_super_admin)
        db_session.add(user)
        db_session.flush()

        if not is_super_admin:
            payload = {
            "user_id": user.id,
            "pin": f"{pin_number}",
            "rfid": f"{rfid_serial_number}",
            "relay_pin": get_locker_by_id.relay_pin,
            "is_active": True
        }
            json_payload = json.dumps(payload)
            mqtt_client.publish(os.getenv("MQTT_TOPIC"), json_payload)

        if id_number:
            user_credentials = UserCredential(user_id=user.id, locker_id=locker_number,
                                          rfid_serial_number=rfid_serial_number, pin_number=pin_number)
            db_session.add(user_credentials)
        db_session.commit()
        
    
    except Exception as e:
        db_session.rollback()
        raise e


                                    
def get_user_by_id(user_id):
    try:
        user = (db_session.query(User)
                .options(joinedload(User.credentials).joinedload(UserCredential.locker))
                .filter(User.id == user_id)
                .first())
        return user
    except Exception as e:
        db_session.rollback()
        raise e


def get_user_by_email(email):
    try:
        user = (db_session.query(User)
                .options(joinedload(User.credentials).joinedload(UserCredential.locker))
                .filter(User.email == email)
                .first())
        return user
    except Exception as e:
        db_session.rollback()
        raise e


def serialize_user(user):
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "id_number": user.id_number,
        "address": user.address,
        "is_super_admin": user.is_super_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "credentials": [
            {
                "id": cred.id,
                "rfid_serial_number": cred.rfid_serial_number,
                "pin_number": cred.pin_number,
                "is_current_holder": cred.is_current_holder,
                "locker": {
                    "id": cred.locker.id,
                    "name": cred.locker.name,
                    "relay_pin": cred.locker.relay_pin,
                    "is_available": cred.locker.is_available
                } if cred.locker else None
            }
            for cred in user.credentials
        ]
    }


def AddLocker(locker_name, relay_pin, created_by, is_available=True):
    try:
        locker = Locker(name=locker_name, relay_pin=relay_pin, is_available=is_available, created_by=created_by)
        db_session.add(locker)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e


def get_all_lockers():
    try:
        lockers = db_session.query(Locker).all()
        return lockers
    except Exception as e:
        db_session.rollback()
        raise e


def UpdateLockerAvailability(locker_id, is_available):
    try:
        locker = db_session.query(Locker).filter_by(id=locker_id).first()
        locker.is_available = is_available
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e


def get_user_locker_info(user_id):
    try:
        user = (db_session.query(User)
                .options(joinedload(User.credentials).joinedload(UserCredential.locker))
                .filter(User.id == user_id)
                .first())
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        locker_info = [
            {
                "locker_id": cred.locker.id,
                "locker_name": cred.locker.name,
                "relay_pin": cred.locker.relay_pin,
                "is_available": cred.locker.is_available,
                "rfid_serial_number": cred.rfid_serial_number,
                "pin_number": cred.pin_number
            }
            for cred in user.credentials if cred.locker
        ]

        return locker_info

    except Exception as e:
        db_session.rollback()
        raise e
    

def get_user_creds(user_id):
    try:
        # Query the database for the user's credentials
        user_credentials = (db_session.query(UserCredential)
                            .options(joinedload(UserCredential.locker))
                            .filter(UserCredential.user_id == user_id)
                            .all())
        
        # If no credentials are found, raise an HTTPException
        if not user_credentials:
            raise HTTPException(status_code=404, detail="User credentials not found")

        # Serialize the credentials
        creds_info = [
            {
                "id": cred.id,
                "rfid_serial_number": cred.rfid_serial_number,
                "pin_number": cred.pin_number,
                "is_current_holder": cred.is_current_holder,
                "is_active": cred.is_active,  # Add is_active status
                "locker": {
                    "id": cred.locker.id,
                    "name": cred.locker.name,
                    "relay_pin": cred.locker.relay_pin,
                    "is_available": cred.locker.is_available
                } if cred.locker else None
            }
            for cred in user_credentials
        ]

        return creds_info

    except Exception as e:
        db_session.rollback()
        raise e