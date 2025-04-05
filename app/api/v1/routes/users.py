import json
import traceback
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.core.config import get_supabase_client, templates
from app.models.schemas import *
from app.services.admin_service import get_user_by_id, get_user_creds, get_user_locker_info, get_user_session, is_super_admin
from app.services.history_logs import log_history
from app.models.database import *
from app.models.models import *
from app.services.mqtt import mqtt_client


load_dotenv()

router = APIRouter()


@router.get("/register-super-admin")
async def show_super_admin_form(request: Request):
    return templates.TemplateResponse("superadmin.html", {"request": request})


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


@router.post('/validate-pin')
async def validate_pin(request: Request, pin_request: PinValidationRequest):
    user_id = get_user_session(request).get('id')
    user_creds = get_user_creds(user_id)
    print(user_creds[0])
   
    # First, check if user credentials exist
    if not user_creds:
        return {"valid": False, "message": "User credentials not found"}

    # Then, check if the account is active
    if not user_creds[0].get('is_active', False):
        return {"valid": False, "message": "Account deactivated"}

    # If the account is active, validate the PIN
    if str(pin_request.pin) == str(user_creds[0]['pin_number']):
        return {"valid": True}
    else:
        return {"valid": False, "message": "Invalid PIN"}
    

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
    try:
        # Fetch the user from the database
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        print(password_data)
        
        # Get the user's email
        user_email = user.email
        
        # Search for the user in Supabase by email
        supabase_users = supabase.auth.admin.list_users()
        supabase_user = next((u for u in supabase_users if u.email == user_email), None)
        
        if not supabase_user:
            raise HTTPException(status_code=404, detail="User not found in Supabase")
        
        # Update password using Supabase
        try:
            response = supabase.auth.admin.update_user_by_id(
                supabase_user.id,
                {"password": password_data.new_password}
            )
            
            # If we reach this point, the update was successful
            # Log the password change action
            log_history(user_id=user_id, action="Password updated")
            
            return JSONResponse(content={"message": "Password updated successfully"}, status_code=200)
        except Exception as supabase_error:
            # If there's an exception, it means the update failed
            raise HTTPException(status_code=400, detail=str(supabase_error))
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating password: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"message": f"Error updating password: {str(e)}"}, status_code=500)


@router.patch("/update-pin")
async def update_pin(request: Request, pin_data: PinUpdate):
    user_id = get_user_session(request).get('id')
 
    payload = {
        "user_id": user_id,
        "pin": pin_data.new_pin,
        "rfid": get_user_session(request).get('credentials')[0].get('rfid_serial_number')}
    
    json_payload = json.dumps(payload)
    
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

        mqtt_client.publish(os.getenv("MQTT_TOPIC"), json_payload)
        request.session.get("user")['credentials'][0]['pin_number'] = pin_data.new_pin
        
        # Log the PIN update action
        log_history(user_id=user_id, action="Update PIN Number")
        
        return JSONResponse(content={"message": "PIN updated successfully"}, status_code=200)
    except HTTPException as he:
        db_session.rollback()
        raise he
    except Exception as e:
        db_session.rollback()
        print(f"Error updating PIN: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"message": f"Error updating PIN: {str(e)}"}, status_code=500)