import json
import os
import shutil
import time
import traceback
from uuid import uuid4
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.core.config import get_supabase_client, templates
from app.models.schemas import *
from app.services.admin_service import get_user_by_id, get_user_creds, get_user_creds_by_user_id, get_user_locker_info, get_user_session, is_super_admin, update_user_hash_password
from app.services.history_logs import log_history
from app.models.database import *
from app.models.models import *
from app.services.mqtt import mqtt_client, is_globally_locked, get_lockdown_status, set_web_lockdown, publish_credential_update
from datetime import datetime, timedelta

from app.services.notification import notify_password_change, notify_pin_change
from app.services.hash_password import hash_password, verify_password



load_dotenv()

router = APIRouter()


@router.get("/register-super-admin")
async def show_super_admin_form(request: Request):
    return templates.TemplateResponse("superadmin.html", {"request": request})

@router.get('/sign-up', response_class=HTMLResponse)
async def sign_up_page(request: Request):
    """Render the sign-up page."""
    return templates.TemplateResponse('sign-up.html', {'request': request})

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse('login.html', {'request': request})


@router.get('/my-locker')
async def my_locker(request: Request):
    return templates.TemplateResponse('my-locker.html', {'request': request})


@router.get('/profile')
async def profile_page(request: Request):
    user_session = get_user_session(request)
    user = get_user_by_id(user_session['id'])
    return templates.TemplateResponse('profile.html', {'request': request, "user": user})


@router.get('/reset-email-password')
async def reset_password_page(request: Request):
    return templates.TemplateResponse('reset-email-password.html', {'request': request})


@router.get('/new-password')
async def new_password_page(request: Request):
    return templates.TemplateResponse('new-password.html', {'request': request})


@router.get('/history')
async def history_page(request: Request):
    return templates.TemplateResponse('history-logs.html', {'request': request})


@router.get('/users', response_class=HTMLResponse, dependencies=[Depends(is_super_admin)])
async def user_list_page(request: Request):
    return templates.TemplateResponse('users.html', {'request': request})


@router.get('/settings')
async def settings_page(request: Request):
    user = get_user_by_id(get_user_session(request).get('id'))
    return templates.TemplateResponse('settings.html', {'request': request, "user": user})


@router.get('/contact-us')
async def contact_us_page(request: Request):
    return templates.TemplateResponse('contact-us.html', {'request': request})


@router.get("/lockers")
def locker_management_page(request: Request):
    return templates.TemplateResponse("lockers.html", {"request": request})


@router.get("/logout")
async def logout(request: Request):
    user_id = get_user_session(request).get('id')
    log_history(user_id=user_id, action="Logged out")
    del request.session["user"]

    return RedirectResponse(url="/login")


@router.get("/s")
def search_page(request: Request):
    return request.session


@router.get("/c")
def c_(request: Request):
    return request.session.clear()


class PinLockoutRequest(BaseModel):
    user_id: int

@router.post("/lockout")
def publish_lockout(request: PinLockoutRequest):
    try:
        mqtt_payload = {
            "user_id": str(request.user_id),
            "lockout_duration": 120
        }
        mqtt_client.publish("locker/validate_pin", json.dumps(mqtt_payload))

        print('locked out user {user_id} for 2 minutes')
    except Exception as e:
        print("Error publishing to MQTT:", e)

@router.get("/lockdown-status")
def get_lockdown_status_endpoint():
    """Get current system lockdown status"""
    return get_lockdown_status()

failed_attempts = {} 

@router.post('/validate-pin')
async def validate_pin(request: Request, pin_request: PinValidationRequest):
    user_id = pin_request.user_id

    # Check global lockdown first
    if is_globally_locked():
        lockdown_status = get_lockdown_status()
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": f"System is locked ({lockdown_status['source']}). Please try again later",
                "cooldown": lockdown_status["remaining_seconds"],
                "remaining_attempts": 0,
                "lockdown_source": lockdown_status["source"]
            }
        )

    user_cred = get_user_creds_by_user_id(user_id)

    # Check individual user cooldown
    if user_cred and user_cred.attempt_duration and datetime.now() < user_cred.attempt_duration:
        remaining_time = (user_cred.attempt_duration - datetime.now()).seconds
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": f"Too many attempts. Please try again in {remaining_time} seconds",
                "cooldown": remaining_time,
                "remaining_attempts": 0
            }
        )

    user_creds = get_user_creds(user_id)

    if not user_creds:
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": "User credentials not found"
            }
        )

    if not user_creds[0].get('is_active', False):
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": "Account deactivated"
            }
        )

    # Check PIN
    if str(pin_request.pin) == str(user_creds[0]['pin_number']):
        if user_id in failed_attempts:
            del failed_attempts[user_id]
        return {"valid": True}

    # Handle failed attempts
    if user_id not in failed_attempts:
        failed_attempts[user_id] = {'count': 0}

    failed_attempts[user_id]['count'] += 1

    if failed_attempts[user_id]['count'] >= 3:
        lockout_time = datetime.now() + timedelta(seconds=120)
        failed_attempts[user_id]['lockout_time'] = lockout_time

        # Set global lockdown from web
        set_web_lockdown(user_id, 120)

        # Update individual user DB cooldown
        if user_cred:
            user_cred.attempt_duration = lockout_time
            try:
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                print("DB commit error:", e)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "valid": False,
                        "message": "Failed to update lockout time in database",
                        "cooldown": 120,
                        "remaining_attempts": 0
                    }
                )

        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "message": "Too many failed attempts. System locked for 2 minutes",
                "cooldown": 120,
                "remaining_attempts": 0,
                "lockdown_source": "web"
            }
        )

    remaining_attempts = 3 - failed_attempts[user_id]['count']
    raise HTTPException(
        status_code=400,
        detail={
            "valid": False,
            "message": f"Invalid PIN. {remaining_attempts} attempts remaining",
            "remaining_attempts": remaining_attempts
        }
    )

# ------- Update user profile -------
@router.patch("/update-profile")
async def update_profile(request: Request, profile_data: ProfileUpdate):
    user_id = get_user_session(request).get('id')
    
    try:
        user = db_session.query(User).filter(User.id == user_id).one()
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = profile_data.dict(exclude_unset=True)
    
    # Prepare action details
    action_details = []
    for key, new_value in update_data.items():
        try:
            old_value = getattr(user, key)
            if old_value != new_value:
                action_details.append(f"{key}: {old_value} > {new_value}")
                setattr(user, key, new_value)
        except Exception as e:
            print(f"Error updating field {key}: {str(e)}")
            traceback.print_exc()
    
    if action_details:
        try:
            # Log the action
            log_details = "Update profile: " + "; ".join(action_details)
            log_history(user_id=user_id, action=log_details)
            
            db_session.commit()
            return JSONResponse(content={"message": "Profile updated successfully"}, status_code=200)
        except Exception as e:
            db_session.rollback()
            print(f"Error committing changes: {str(e)}")
            traceback.print_exc()
            return JSONResponse(content={"message": f"Error updating profile: {str(e)}"}, status_code=500)
    else:
        return JSONResponse(content={"message": "No changes detected"}, status_code=200)
    

@router.patch("/update-password")
async def update_password(request: Request, password_data: PasswordUpdate):
    user_id = get_user_session(request).get('id')
    supabase = get_supabase_client()
    user = get_user_by_id(user_id)

    try:        

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not verify_password(password_data.current_password, user.hashed_password):
            return JSONResponse(content={"message": "Invalid current password"}, status_code=400)
            
        
        
        user_email = user.email

        # Find user in Supabase
        supabase_users = supabase.auth.admin.list_users()
        supabase_user = next((u for u in supabase_users if u.email == user_email), None)

        if not supabase_user:
            raise HTTPException(status_code=404, detail="User not found in Supabase")

        # Update the password
        supabase.auth.admin.update_user_by_id(
            supabase_user.id,
            {"password": password_data.new_password}
        )

        # Log password update
        log_history(user_id=user_id, action="Password updated")

        # Send password change email
        notify_password_change(user_email)
        update_user_hash_password(user_id, password_data.new_password)

        return JSONResponse(content={"message": "Password updated successfully"}, status_code=200)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating password: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"message": f"Error updating password: {str(e)}"}, status_code=500)


@router.patch("/update-pin")
async def update_pin(request: Request, pin_data: PinUpdate):
    user_id = get_user_session(request).get('id')

    try:
        user_cred = db_session.query(UserCredential).filter(UserCredential.user_id == user_id).one()

        if not user_cred:
            raise HTTPException(status_code=404, detail="User credentials not found")

        if str(pin_data.current_pin) != str(user_cred.pin_number):
            raise HTTPException(status_code=400, detail="Incorrect current PIN")

        # Update the PIN in the UserCredential model
        user_cred.pin_number = pin_data.new_pin

        # Commit the changes to the database
        db_session.commit()

        # Send credential update to ESP32 with correct data from database
        relay_pin = user_cred.locker.relay_pin if user_cred.locker else 15
        publish_credential_update(
            user_id=user_id,
            pin=pin_data.new_pin,
            rfid=user_cred.rfid_serial_number,
            relay_pin=relay_pin,
            is_active=user_cred.is_active
        )

        request.session.get("user")['credentials'][0]['pin_number'] = pin_data.new_pin

        # Log the PIN update action
        log_history(user_id=user_id, action="Update PIN Number")
        user = get_user_by_id(user_id)
        notify_pin_change(user.email)

        return JSONResponse(content={"message": "PIN updated successfully"}, status_code=200)
    except HTTPException as he:
        db_session.rollback()
        raise he
    except Exception as e:
        db_session.rollback()
        print(f"Error updating PIN: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"message": f"Error updating PIN: {str(e)}"}, status_code=500)
    

#------- Update user PFP -------

@router.post("/upload-profile-photo")
async def upload_profile_photo(request: Request, profile_photo: UploadFile = File(...)):
    UPLOAD_DIR = "app/static/uploads/profile_photos"

    if not profile_photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = profile_photo.filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(profile_photo.file, buffer)
    image_url = f"{UPLOAD_DIR}/{filename}"

    user = db_session.query(User).filter(User.id == get_user_session(request).get('id')).first()

    if user:
        user.avatar = image_url

        if request.session.get("user")['avatar']:
            try:
                old_avatar_path = request.session.get("user")['avatar']
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)

            except Exception as e:
                print(f"Error removing old profile photo: {str(e)}")
                
        request.session.get("user")['avatar'] = image_url
        db_session.commit()
        log_history(user_id=get_user_session(request).get('id'), action="Update Profile Photo")
    else:
        raise HTTPException(status_code=404, detail="Invalid User")

    return JSONResponse(content={"message": "Photo uploaded successfully", "url": image_url})


@router.delete("/delete-profile-photo")
async def delete_profile_photo(request: Request):

    if not get_user_session(request) or not get_user_session(request).get("avatar"):
        raise HTTPException(status_code=400, detail="No profile photo found.")

    file = request.session["user"]["avatar"] 

    if os.path.exists(file):
        os.remove(file)
        request.session["user"]["avatar"] = None 
        user = db_session.query(User).filter(User.id == get_user_session(request).get('id')).first()
        user.avatar = None
        db_session.commit()

        log_history(user_id=get_user_session(request).get('id'), action="Delete Profile Photo")

        return JSONResponse(content={"message": "Profile photo deleted successfully"})
    else:
        raise HTTPException(status_code=404, detail="File not found")
