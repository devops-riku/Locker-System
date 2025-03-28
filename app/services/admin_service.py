from app.models.database import *
from app.models.models import *
from sqlalchemy.orm import *

def CreateUser(first_name, last_name, id_number, address, email, password, locker_number, rfid_serial_number, pin_number):
    try:
        user = User(first_name=first_name, last_name=last_name, id_number=id_number, address=address, email=email)
        db_session.add(user)
        db_session.flush()

        user_credentials = UserCredential(user_id=user.id, locker_id=locker_number, rfid_serial_number=rfid_serial_number, pin_number=pin_number)
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
    

def AddLocker(locker_name, relay_pin, is_available=True):
    try:
        locker = Locker(name=locker_name, relay_pin=relay_pin, is_available=is_available)
        db_session.add(locker)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e
    
def get_all_lockers():
    try:
        lockers = Locker.query.all()
        return lockers
    except Exception as e:
        db_session.rollback()
        raise e


def UpdateLockerAvailability(locker_id, is_available):
    try:
        locker = Locker.query.filter_by(id=locker_id).first()
        locker.is_available = is_available
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e