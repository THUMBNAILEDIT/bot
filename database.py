from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_client_data(channel_id: str):
    response = supabase.table("clientbase").select("*").eq("slack_id", channel_id).execute()
    return response.data[0] if response.data else None

def fetch_client_data_by_task_id(task_id: str):
    response = supabase.table("clientbase").select("*").like("current_tasks", f"%{task_id}%").execute()
    return response.data[0] if response.data else None

def update_client_credits(channel_id: str, new_credits: int):
    supabase.table("clientbase").update({"current_credits": new_credits}).eq("slack_id", channel_id).execute()

def update_client_current_tasks(channel_id: str, task_id: str):
    client = fetch_client_data(channel_id)
    if client:
        current_tasks = client.get("current_tasks", "")
        tasks_list = current_tasks.split(",") if current_tasks else []
        tasks_list.append(task_id)
        updated_tasks = ",".join(tasks_list)
        supabase.table("clientbase").update({"current_tasks": updated_tasks}).eq("slack_id", channel_id).execute()

def remove_task_from_current_tasks(channel_id: str, task_id: str):
    client = fetch_client_data(channel_id)
    if client:
        current_tasks = client.get("current_tasks", "")
        tasks_list = current_tasks.split(",") if current_tasks else []
        if task_id in tasks_list:
            tasks_list.remove(task_id)
        updated_tasks = ",".join(tasks_list)
        supabase.table("clientbase").update({"current_tasks": updated_tasks}).eq("slack_id", channel_id).execute()

def update_client_thread_mapping(channel_id: str, thread_ts: str, task_id: str):
    client = fetch_client_data(channel_id)
    if client:
        current_mappings = client.get("thread_mappings", {}) or {}
        current_mappings[thread_ts] = task_id
        supabase.table("clientbase").update({"thread_mappings": current_mappings}).eq("slack_id", channel_id).execute()