from supabase import create_client, Client
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_client_by_slack_id(slack_id: str):
    try:
        response = supabase.table("clientbase").select("*").eq("slack_id", slack_id).execute()

        if response.data:
            return response.data[0]
        else:
            return None
    except Exception as e:
        print(f"Error fetching client: {e}")
        return None