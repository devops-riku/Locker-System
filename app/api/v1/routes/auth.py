import json
from fastapi import APIRouter, HTTPException, Request
from app.core.config import get_supabase_client
from app.core.config import templates
from app.models import schemas
from app.services.admin_service import CreateUser, RegisterUser, get_user_by_email, serialize_user
from app.services.auth_service import create_auth_user, init_reset_password, send_reset_password_link
from app.services.history_logs import log_history
from app.services.jwt_decode import JWTDecode

router = APIRouter()


@router.post("/login")
async def login_auth(request: Request, user: schemas.UserLoginRequest):
    try:
        supabase = get_supabase_client()
        
        # Attempt to sign in the user
        response = supabase.auth.sign_in_with_password({
            "email": user.email.strip().lower(),
            "password": user.password,
            "timeout": 60
        })
        
    
        # Fetch user data
        user_data = get_user_by_email(user.email)

        if not user_data.is_active:
            raise HTTPException(status_code=400, detail="Account is not activated. Contact your administrator to activate your account.")
        request.session['user'] = serialize_user(user_data)

        # Log login history
        log_history(user_id=user_data.id, action="Logged in")

        return {"message": "Login successful!"}

    except KeyError:
        raise HTTPException(status_code=500, detail="Unexpected response from authentication service")
    
    except Exception as e:
        if "email not confirmed" in str(e).lower():
            raise HTTPException(status_code=400, detail="Email not confirmed. Please check your email for verification.")
        
        raise HTTPException(status_code=500, detail=f"{str(e)}")
    
@router.post("/register")
async def register_user(user: schemas.RegisterUserRequest):
    try:
        supabase = get_supabase_client()
        print(user)
        # Attempt to create the user in the database
        auth_user_list = supabase.auth.admin.list_users()
        user_exists = any(user.email.strip().lower() == u.email for u in auth_user_list)
        if user_exists:
            raise HTTPException(status_code=400, detail="Email is already in use in authentication system.")
        
         # Attempt to create the authentication user
        try:
            create_auth_user(email=user.email, password=user.password, email_confirm=True)
        except Exception as e:
            print(f"Error in create_auth_user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error in creating authentication user: {str(e)}")
    
        try:
            CreateUser(
                first_name=user.first_name,
                last_name=user.last_name,
                address=user.address,
                email=user.email.strip().lower(),
                locker_number=None,
                rfid_serial_number=None,
                pin_number=user.pin_number,
                created_by=None,
                is_super_admin=False,
                is_active=False
            )
        except Exception as e:
            print(f"Error in CreateUser: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error in creating user: {str(e)}")


        return {"message": "Registration Successful!"}
    
    except Exception as e:
        # Catch any unhandled exception that might happen during the process
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    

    

# For Logout


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
    
    email_from_token = JWTDecode(access_token)
    try:              
        # init_reset_password(access_token, new_password)
        if get_user_by_email(email_from_token.get("email", None)):
            log_history(user_id=get_user_by_email(email_from_token.get("email", None)).id, action="Update Email Password")
        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
