from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.config import templates

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
    return templates.TemplateResponse('profile.html', {'request': request})

@router.get('/reset-password')
async def reset_password_page(request: Request):
    return templates.TemplateResponse('reset-password.html', {'request': request})

@router.get('/history')
async def history_page(request: Request):
    return templates.TemplateResponse('history-logs.html', {'request': request})

@router.get('/users')
async def user_list_page(request: Request):
    return templates.TemplateResponse('users.html', {'request': request})

