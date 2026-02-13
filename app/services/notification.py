from dotenv import load_dotenv
import resend
import os

# Load environment variables from .env
load_dotenv()

# Set Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

# General function to send an email
def send_email_notification(to_email: str, subject: str, html: str):
    params: resend.Emails.SendParams = {
        "from": "My Locker <info@my-locker.site>",
        "to": [to_email],
        "subject": subject,
        "html": html
    }

    email = resend.Emails.send(params)
    print(email)
    return email

# 1. PIN change notification
def notify_pin_change(to_email: str):
    subject = "Your PIN was changed"
    html = """
        <p>Hello,</p>
        <p>Your account PIN was successfully changed.</p>
        <p>If you didn't perform this action, please contact support immediately.</p>
    """
    return send_email_notification(to_email, subject, html)

# 2. Password change notification
def notify_password_change(to_email: str):
    subject = "Your Password was changed"
    html = """
        <p>Hello,</p>
        <p>Your password has been updated successfully.</p>
        <p>If this wasn't you, please reset your password or contact support.</p>
    """
    return send_email_notification(to_email, subject, html)

# 3. Account activation notification
def notify_account_activated(to_email: str, current_pin: str):
    subject = "Your Account Has Been Activated"
    html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Your Account is Activated</h2>
            <p>Hello,</p>
            <p>Your <strong>My Locker</strong> account has been successfully activated.</p>
            <p>Below is your Locker PIN. Please keep it safe and do not share it with anyone.</p>
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #6c757d;">Your Locker PIN</p>
                <p style="margin: 5px 0 0; font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #2c3e50;">{current_pin}</p>
            </div>
            <p style="color: #6c757d; font-size: 12px;">If you did not request this activation, please contact your administrator.</p>
        </div>
    """
    return send_email_notification(to_email, subject, html)
