from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from supabase import create_client
from datetime import datetime
import os

from app.services.utc_converter import utc_to_ph

load_dotenv()


templates = Jinja2Templates(directory="app/templates")

def get_supabase_client():
    """Returns a new Supabase client instance."""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def pht(value):
    pht_time = utc_to_ph(str(value))
    return pht_time


templates.env.filters["pht"] = pht