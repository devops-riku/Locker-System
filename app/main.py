import os
import threading
import time
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Import API version routes
from app.api.v1.routes import mqtt_trigger, users as users_v1, auth as auth_v1, admin as admin_v1
from app.core.init_db import init_db
from app.services.admin_service import get_user_session, user_is_logged_in
from app.services.admin_service import user_is_logged_in, check_super_admin
from app.services.mqtt import mqtt_setup, mqtt_client
# from app.api.v2.routes import users as users_v2, auth as auth_v2, admin as admin_v2
from app.services.mqtt import mqtt_client
load_dotenv()

init_db()
# Initialize FastAPI
app = FastAPI(title="Locker System", version="1.0")
app.mount("/app/static", StaticFiles(directory="app/static"), name="static")


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers['Content-Security-Policy'] = "upgrade-insecure-requests"
        return response



@app.middleware("http")
async def sessions_middleware(request: Request, call_next):
    # List of paths that should not be checked for session
    public_paths = [
        "/login", "/api/v1/auth/login", "/reset-email-password", "/new-password",
        "/api/v1/auth/request-password-reset", "/api/v1/auth/reset-password",
        "/register-super-admin", "/admin/register-super-admin"
    ]

    # Bypass middleware for static files
    if request.url.path.startswith("/app/static"):
        return await call_next(request)

    # Check if there is no super admin
    if not check_super_admin() and request.url.path not in ["/register-super-admin", "/admin/register-super-admin"]:
        # Redirect to register super admin if no super admin exists
        return RedirectResponse(url="/register-super-admin")

    # Check if there is a super admin and the request is for the register-super-admin path
    if check_super_admin() and request.url.path == "/register-super-admin":
        # Redirect to home or dashboard if super admin exists
        return RedirectResponse(url="/")

    # Check if the user is logged in
    user_logged_in = user_is_logged_in(request)

    if user_logged_in and request.url.path in public_paths:
        # Redirect logged-in users away from public paths
        return RedirectResponse(url="/")  # Redirect to a default logged-in page, e.g., dashboard

    if not user_logged_in and request.url.path not in public_paths:
        # Redirect to login if user is not logged in and trying to access a protected path
        return RedirectResponse(url="/login")

    # Proceed with the request
    response = await call_next(request)
    return response

# Register API v1 routes
app.include_router(users_v1.router, tags=["Users v1"])
app.include_router(auth_v1.router, prefix="/api/v1/auth", tags=["Auth v1"])
app.include_router(admin_v1.router, tags=["Admin v1"])

# Route for MQTT
app.include_router(mqtt_trigger.router, prefix="/mqtt", tags=["MQTT"])

app.add_middleware(SessionMiddleware, secret_key="@LockerSystem!")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(ContentSecurityPolicyMiddleware)

# Start MQTT setup in background
threading.Thread(target=mqtt_setup, daemon=True).start()

# Root Endpoint
@app.get("/", tags=["Root"])
async def root(request: Request):
    if get_user_session(request).get('is_super_admin', False):
        return RedirectResponse(url="/users")
    return RedirectResponse(url="/my-locker")




def debounce(wait):
    """
    Decorator that will postpone a function's
    execution until after wait seconds
    have elapsed since the last time it was invoked.
    """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = threading.Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator

@debounce(1)  # 1 second debounce
def check_mqtt():
    # This function will be called at most once per second
    mqtt_client.loop(timeout=0.1)

def run():
    mqtt_setup()

    try:
        while True:
            check_mqtt()
            time.sleep(0.1)  # Sleep for a short time to prevent CPU hogging
    except KeyboardInterrupt:
        print("👋 Shutting down...")
        mqtt_client.disconnect()

if __name__ == "__main__":
    run()