from datetime import datetime
import pytz

def utc_to_ph(utc_datetime_str):
    # Parse the UTC datetime string into a datetime object
    utc_datetime = datetime.fromisoformat(utc_datetime_str)

    # Define the UTC timezone
    utc_timezone = pytz.utc

    # Define the target timezone (UTC+8:00)
    ph_timezone = pytz.timezone('Asia/Singapore')  # or any other timezone that corresponds to UTC+8:00

    # Localize the datetime to UTC
    utc_datetime = utc_timezone.localize(utc_datetime)

    # Convert the datetime to the target timezone
    ph_datetime = utc_datetime.astimezone(ph_timezone)

    # Format the datetime as a string in the desired format
    return ph_datetime.strftime('%m-%d-%Y | %I:%M:%S %p')