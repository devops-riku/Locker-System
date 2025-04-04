from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.config import templates
from app.models.schemas import *
from app.services.admin_service import get_user_by_id, get_user_session, is_super_admin
from app.services.history_logs import log_history

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
    del request.session["user"]
    return RedirectResponse(url="/login")





@router.get("/s")
def search_page(request: Request):
    return request.session


@router.get("/c")
def c_(request: Request):
    return request.session.clear()
