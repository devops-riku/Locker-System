from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import API version routes
from app.api.v1.routes import users as users_v1, auth as auth_v1, admin as admin_v1
from app.core.init_db import init_db
# from app.api.v2.routes import users as users_v2, auth as auth_v2, admin as admin_v2


init_db()

# Initialize FastAPI
app = FastAPI(title="Locker System", version="1.0")
app.mount("/app/static", StaticFiles(directory="app/static"), name="static")

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Register API v1 routes
app.include_router(users_v1.router, tags=["Users v1"])
app.include_router(auth_v1.router, prefix="/api/v1/auth", tags=["Auth v1"])
app.include_router(admin_v1.router, tags=["Admin v1"])


# Root Endpoint
@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to FastAPI with API Versioning 🚀",
        "versions": {
            "v1": "/api/v1/"
        }
    }

