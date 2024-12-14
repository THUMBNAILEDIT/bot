from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_client_data(channel_id: str):
    response = supabase.table("clientbase").select("*").eq("slack_id", channel_id).execute()
    return response.data[0] if response.data else None

def fetch_client_data_by_task_id(task_id):
    response = supabase.table("clientbase").select("*").eq("current_task", task_id).execute()
    return response.data[0] if response.data else None

def update_client_credits(channel_id: str, new_credits: int):
    supabase.table("clientbase").update({"current_credits": new_credits}).eq("slack_id", channel_id).execute()

def update_client_current_task(channel_id: str, task_id: str):
    supabase.table("clientbase").update({"current_task": task_id}).eq("slack_id", channel_id).execute()