from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import desc

from app.models.database import db_session
from app.models.models import History, Locker, User, UserCredential
from app.models.schemas import AddLockerRequest, CreateUserRequest, SuperAdminCreate, UpdateLockerRequest, UpdateUserRequest
from app.services.admin_service import AddLocker, CreateUser, UpdateLockerAvailability, get_user_session, is_super_admin
from app.services.auth_service import create_auth_user, delete_auth_user
from datetime import datetime
import pytz

from app.services.utc_converter import utc_to_ph

router = APIRouter(prefix="/admin")


# Users
@router.post("/create-user")
async def create_user(user: CreateUserRequest, request: Request):
    create_auth_user(user.email, user.password)
    CreateUser(user.first_name, user.last_name, user.id_number, user.address, user.email,
               user.locker_number, user.rfid_serial_number, user.pin_number)
    UpdateLockerAvailability(locker_id=user.locker_number, is_available=False)
    return {"message": "User created successfully"}


@router.get("/user-lists", dependencies=[Depends(is_super_admin)])
async def get_user_lists(page_number: int = Query(1, ge=1), page_size: int = Query(10, ge=1)):

    
    # Get total number of users
    total_users = db_session.query(User).filter(User.is_super_admin == False).count()
    total_pages = (total_users + page_size - 1) // page_size

    # Prevent requesting out-of-range pages
    if page_number > total_pages:
        return {
            "total": total_users,
            "total_pages": total_pages,
            "page_number": page_number,
            "page_size": page_size,
            "results": []
        }

    # Calculate offset
    offset = (page_number - 1) * page_size

    # Query the correct page
    users = (
        db_session.query(User)
        .filter(User.is_super_admin == False)
        .order_by(User.id)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    user_list = []
    for user in users:
        user_dict = {
            "id": user.id,
            "Name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "id_number": user.id_number,
            "credentials": [
                {
                    "locker": {
                        "name": cred.locker.name if cred.locker else None
                    }
                }
                for cred in user.credentials
            ]
        }
        user_list.append(user_dict)

    return {
        "total": total_users,
        "total_pages": total_pages,
        "page_number": page_number,
        "page_size": page_size,
        "results": user_list
    }


@router.get("/user/{user_id}")
async def get_user(user_id: int):
    user = db_session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "id_number": user.id_number,
        "address": user.address,
        "credentials": [
            {
                "locker": {
                    "id": cred.locker.id if cred.locker else None,
                    "name": cred.locker.name if cred.locker else None
                }
            }
            for cred in user.credentials
        ]
    }


@router.put("/user/{user_id}")
async def update_user(user_id: int, user: UpdateUserRequest):
    update_user = db_session.query(User).filter(User.id == user_id).first()
    update_user.first_name = user.first_name
    update_user.last_name = user.last_name
    update_user.id_number = user.id_number
    update_user.address = user.address

    user_credentials = db_session.query(UserCredential).filter(UserCredential.user_id == user_id).first()
    user_credentials.locker_id = user.assigned_locker
    db_session.commit()
    return {"message": "User updated successfully."}


@router.delete("/user/{user_id}")
async def delete_user(user_id: int):
    user = db_session.query(User).filter(User.id == user_id).first()
    locker_id = db_session.query(UserCredential).filter(UserCredential.user_id == user_id).first().locker_id
    UpdateLockerAvailability(locker_id=locker_id, is_available=True)
    delete_auth_user(user.email)
    db_session.delete(user)
    db_session.commit()
    return {"message": "User deleted successfully."}


# Lockers
@router.get("/lockers")
def get_lockers():
    return db_session.query(Locker).all()


@router.get("/lockers/{locker_id}")
def get_locker(locker_id: int):
    return db_session.query(Locker).filter(Locker.id == locker_id).first()


@router.post('/add-locker')
async def add_locker(request: Request, data: AddLockerRequest):
    """Handle adding a new locker."""
    try:
        AddLocker(locker_name=data.locker_name, relay_pin=data.relay_pin, created_by=get_user_session().id)
        return {"message": "Locker added successfully."}
    except Exception as e:
        return {"message": "Failed to add locker."}, 500


@router.post("/lockers")
def create_locker(locker: AddLockerRequest):
    new_locker = Locker(name=locker.locker_name, relay_pin=locker.relay_pin, created_by='admin')
    db_session.add(new_locker)
    db_session.commit()
    db_session.refresh(new_locker)
    return new_locker


@router.put("/lockers/{locker_id}")
def update_locker(locker_id: int, locker_data: UpdateLockerRequest):
    locker = db_session.query(Locker).filter_by(id=locker_id).first()
    locker.name = locker_data.locker_name
    locker.relay_pin = locker_data.relay_pin
    locker.is_available = locker_data.is_available
    db_session.commit()
    return {"message": "updated"}


@router.delete("/lockers/{locker_id}")
def delete_locker(locker_id: int):
    db_session.query(Locker).filter(Locker.id == locker_id).delete()
    db_session.commit()
    return {"message": "deleted"}


@router.post("/register-super-admin")
async def register_super_admin(super_admin: SuperAdminCreate):
    # Validate email format


    # Create authentication user and super admin
    create_auth_user(super_admin.email, super_admin.password)
    CreateUser(email=super_admin.email, is_super_admin=True)

    return {"message": "Super admin created successfully."}

   


@router.get("/get_history")
async def get_history(request: Request):
    user = get_user_session(request)

    # Determine the query based on user role
    if user.get('is_super_admin'):
        history_records = db_session.query(History).order_by(desc(History.date_created)).all()
    else:
        history_records = db_session.query(History).filter(History.user_id == user.get('id')).order_by(desc(History.date_created)).all()

    # Serialize the history records
    history_list = [
        {
            "author": f"{record.user.first_name} {record.user.last_name}" if record.user else "Unknown",
            "action": record.action,
            "datetime": utc_to_ph(str(record.date_created))  # Convert to UTC+8:00
        }
        for record in history_records
    ]

    return {"history": history_list}