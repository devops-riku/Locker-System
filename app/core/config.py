from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from supabase import create_client
import os

load_dotenv()


templates = Jinja2Templates(directory="app/templates")

def get_supabase_client():
    """Returns a new Supabase client instance."""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

    return create_client(SUPABASE_URL, SUPABASE_KEY)