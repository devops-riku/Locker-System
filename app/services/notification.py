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

# Example usage (remove these lines in production)
# notify_pin_change("egermino.riku@gmail.com")
# notify_password_change("egermino.riku@gmail.com")
