import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file in the PythonAPI directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Warning: Supabase URL or Key not found. Please create a .env file in the Dashboard/PythonAPI directory with SUPABASE_URL and SUPABASE_KEY.")
    supabase = None
else:
    supabase: Client = create_client(url, key)

def get_db_client() -> Client:
    if supabase is None:
        raise ValueError("Supabase client is not initialized. Check your .env file.")
    return supabase