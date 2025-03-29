import os
from dotenv import load_dotenv
from app.core.config import get_supabase_client

load_dotenv()

supabase = get_supabase_client()


def send_reset_password_link(email):
    reset_redirect_url = f"{os.getenv('HOST_URL')}/new-password"
    try:
        supabase.auth.reset_password_for_email(
            email,
            options={
                "redirect_to": reset_redirect_url,
            }
        )
        return True
    except Exception as e:
        print(f"Error sending reset password link: {str(e)}")
        return False


def init_reset_password(access_token, new_password):
    supabase.auth.set_session(access_token, access_token)
    supabase.auth.update_user({"password": new_password})


def create_auth_user(email, password):
    response = supabase.auth.admin.create_user({
        "email": f'{email}',
        "password": f'{password}',
        "email_confirm": True,
});
    return response

