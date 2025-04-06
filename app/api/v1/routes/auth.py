import json
from fastapi import APIRouter, HTTPException, Request
from app.core.config import get_supabase_client
from app.core.config import templates
from app.models import schemas
from app.services.admin_service import get_user_by_email, serialize_user
from app.services.auth_service import init_reset_password, send_reset_password_link
from app.services.history_logs import log_history

router = APIRouter()


@router.post("/login")
async def login_auth(request: Request, user: schemas.UserLoginRequest):
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password,
            "timeout": 60
        })

        user_data = get_user_by_email(user.email)
        request.session['user'] = serialize_user(user_data)

        log_history(user_id=user_data.id, action="Logged in")
        # TODO: User Session
        return {"message": "Login successful!"}

    except KeyError:
        raise HTTPException(status_code=500, detail="Unexpected response from authentication service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


# For Requesting Password Reset Link
@router.post("/request-password-reset")
async def request_password_reset(request: Request, user: schemas.RequestEmailResetPassword):
    try:
        send_reset_password_link(user.email)
        return {"message": "Reset password link sent successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


# For Changing Password
@router.post("/reset-password")
async def reset_password(request: Request):
    data = await request.json()
    access_token = data.get("access_token")
    new_password = data.get("new_password")

    if not access_token or not new_password:
        raise HTTPException(status_code=400, detail="Missing token or password")

    try:
        init_reset_password(access_token, new_password)
        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
