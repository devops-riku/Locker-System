from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from app.core.config import get_supabase_client
from app.models.database import db_session
from app.models.schemas import *
from app.models.models import *
from app.core.config import templates
from app.services.admin_service import CreateUser
from sqlalchemy.orm import joinedload


router = APIRouter(prefix="/admin")

@router.post("/create-user")
async def create_user(user: CreateUserRequest, request: Request):
    CreateUser(user.first_name, user.last_name, user.id_number, user.address, user.email, user.password, user.locker_number, user.rfid_serial_number, user.pin_number)
    return None


@router.get("/lockers")
def get_lockers():
    lockers = db_session.query(Locker).all()
    return [{"id": locker.id, "name": locker.name, "is_available": locker.is_available} for locker in lockers]


@router.get("/user-lists")
async def get_user_lists(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
):
    # Get total number of users
    total_users = db_session.query(User).count()
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
        "Name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "id_number": user.id_number,
        "address": user.address,
        "credentials": [
            {
                "locker": {
                    "name": cred.locker.name if cred.locker else None
                }
            }
            for cred in user.credentials
        ]
    }