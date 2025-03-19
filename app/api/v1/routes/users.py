from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.core.config import get_supabase_client
from app.models import schemas
from app.core.config import templates
from app.models.models import User
from app.models.database import db_session

router = APIRouter()

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse('login.html', {'request': request})


@router.get('/home')
async def home_page(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@router.get('/profile')
async def profile_page(request: Request):
    return templates.TemplateResponse('profile.html', {'request': request})

@router.get('/reset-password')
async def reset_password(request: Request):
    return templates.TemplateResponse('reset-password.html', {'request': request})

@router.get('/log-history')
async def reset_password(request: Request):
    return templates.TemplateResponse('history-log.html', {'request': request})

@router.get('/users')
async def reset_password(request: Request):
    return templates.TemplateResponse('user-lists.html', {'request': request})