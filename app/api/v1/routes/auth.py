from fastapi import APIRouter, HTTPException, Request
from app.core.config import get_supabase_client
from app.models import schemas




router = APIRouter()

# @router.post("/register_user")
# async def register_auth()

@router.post("/login")
async def login_auth(request: Request, user: schemas.UserLoginRequest):
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password,
            "timeout": 60
        })

        # TODO: User Session
        return {"message": "Login successful!"}

    except KeyError:
        raise HTTPException(status_code=500, detail="Unexpected response from authentication service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")
    

