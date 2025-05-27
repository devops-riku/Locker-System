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


def create_auth_user(email, password, email_confirm=True):
    response = supabase.auth.admin.create_user({
        "email": f'{email}',
        "password": f'{password}',
        "email_confirm": email_confirm,
});
    return response


def delete_auth_user(email):
    all_users = supabase.auth.admin.list_users()
    user_to_delete = next((user for user in all_users if user.email == email), None)
    
    if user_to_delete:
            user_id = user_to_delete.id
            # Delete the user
            supabase.auth.admin.delete_user(user_id)
            print(f"User with email '{email}' deleted.")
    else:
        print("User not found.")


