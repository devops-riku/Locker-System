from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.core.config import get_supabase_client
from app.models import schemas
from app.core.config import templates
from app.models.models import User
from app.models.database import db_session

router = APIRouter(prefix="/admin")
