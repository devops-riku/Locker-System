from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("PIN_TOKEN_SECRET", "@LockerSystem!")
SALT = "pin-change"

serializer = URLSafeTimedSerializer(SECRET_KEY)


def generate_pin_change_token(user_id: int) -> str:
    """Generate a signed, time-limited token embedding the user_id."""
    return serializer.dumps(user_id, salt=SALT)


def verify_pin_change_token(token: str, max_age_seconds: int = 86400) -> int:
    """
    Verify and decode the token. Returns user_id if valid.
    Default expiry: 24 hours (86400 seconds).
    Raises SignatureExpired if token is too old.
    Raises BadSignature if token is tampered with.
    """
    return serializer.loads(token, salt=SALT, max_age=max_age_seconds)
