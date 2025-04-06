from app.models.models import History
from app.models.database import db_session


def log_history(user_id, action):
    try:
        # Create a History entry with the payload as a JSON object
        history_entry = History(user_id=user_id, action=action)
        db_session.add(history_entry)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print(f"Error logging history: {e}")
    finally:
        db_session.close()