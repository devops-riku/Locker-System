from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.config import templates
from app.services.admin_service import get_user_by_id

router = APIRouter()

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse('login.html', {'request': request})

@router.get('/my-locker')
async def my_locker(request: Request):
    return templates.TemplateResponse('my-locker.html', {'request': request})

@router.get('/profile')
async def profile_page(request: Request):
    user = get_user_by_id(1)  # Replace with actual user fetching logic
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

@router.get('/users')
async def user_list_page(request: Request):
    return templates.TemplateResponse('users.html', {'request': request})


@router.get('/settings')
async def settings_page(request: Request):
    user = get_user_by_id(1) 
    return templates.TemplateResponse('settings.html', {'request': request, "user": user})
