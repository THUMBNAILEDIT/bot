import os
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from dotenv import find_dotenv, load_dotenv
from flask import Flask, request, jsonify
from supabase import create_client, Client
import requests
from slack_sdk.errors import SlackApiError

load_dotenv(find_dotenv())

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ASANA_ACCESS_TOKEN = os.getenv("ASANA_ACCESS_TOKEN")
ASANA_PROJECT_ID = os.getenv("ASANA_PROJECT_ID")

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

def fetch_client_data(channel_id: str):
    response = supabase.table("clientbase").select("*").eq("slack_id", channel_id).execute()
    return response.data[0] if response.data else None

def register_webhook_for_task(task_id):
    webhook_url = "https://5b7f-46-211-78-104.ngrok-free.app/asana-webhook"
    url = "https://app.asana.com/api/1.0/webhooks"
    headers = {
        "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "data": {
            "resource": task_id,
            "target": webhook_url
        }
    }
    requests.post(url, headers=headers, json=data)

def create_asana_task(task_name, task_notes, channel_id):
    url = "https://app.asana.com/api/1.0/tasks"
    headers = {
        "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
    }
    data = {
        "data": {
            "name": task_name,
            "notes": task_notes,
            "projects": [ASANA_PROJECT_ID]
        }
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        task_id = response.json().get("data", {}).get("gid")
        if task_id:
            supabase.table("clientbase").update({"current_task": task_id}).eq("slack_id", channel_id).execute()
            register_webhook_for_task(task_id)
            return task_id
        else:
            print("Task ID not found in response.")
    else:
        print(f"Failed to create task: {response.text}")
    return None

@app.command("/request")
def handle_request(ack, command):
    ack()
    description = command["text"]
    channel_id = command["channel_id"]
    client_info = fetch_client_data(channel_id)
    
    if not client_info:
        app.client.chat_postMessage(
            channel=channel_id,
            text="*Error:* We couldn't find your client info. Please ensure your Slack channel is registered."
        )
        return

    if client_info.get('current_credits', 0) <= 0:
        app.client.chat_postMessage(
            channel=channel_id,
            text=(
                f"Sorry {client_info.get('client_name_short', ' ')}, you don't have enough credits to make a request. "
                f"Please visit *<https://www.paddle.com\u200B|our Paddle page>* to refill your credits and then try again."
            )
        )
        return
    
    app.client.chat_postMessage(
        channel=channel_id,
        text=(
            f"Thank you {client_info.get('client_name_short', ' ')}, your thumbnail request has been received! "
            f"Here's the video description you provided: '{description}'\n\n"
            f"Have any questions? Please message *'/help'* to see the FAQ or *'@Bot'* for support!"
        )
    )

    new_credits = client_info.get('current_credits', 0) - 1
    supabase.table("clientbase").update({"current_credits": new_credits}).eq("slack_id", channel_id).execute()

    task_name = f"Request from {client_info['client_name_short']}"
    task_notes = f"""
ORDER INFORMATION
Order type: YouTube Thumbnail
Deliverables:
	• 1920 x 1080 image (.JPG)
	• Project file (.PSD)

CLIENT INFORMATION
Client: {client_info.get('client_name_full', 'Unknown')} 
Client’s channel: {client_info.get('client_channel_name', 'Unknown')} ({client_info.get('client_channel_link', 'Unknown')})

STYLE
Client’s preferences: {client_info.get('client_preferences', 'Unknown')}
Thumbnail examples: {client_info.get('client_thumbnail_examples', 'Unknown')}

TASK DESCRIPTION
Video Description: {description}
"""
    create_asana_task(task_name, task_notes, channel_id)

@app.command("/balance")
def handle_balance(ack, command):
    ack()
    channel_id = command["channel_id"]
    client_info = fetch_client_data(channel_id)
    
    if client_info:
        app.client.chat_postMessage(
            channel=channel_id,
            text=(
                f"Hi {client_info.get('client_name_short', ' ')}! "
                f"You currently have *{client_info.get('current_credits', 'N/A')}/10* credits left. "
                f"Running a little low? Visit *<https://www.paddle.com\u200B|our Paddle page>* to refill the tank!"
            )
        )
    else:
        app.client.chat_postMessage(
            channel=channel_id,
            text="*Error:* We couldn't find your client info. Please ensure your Slack channel is registered.\n\n"
        )

@flask_app.route("/asana-webhook", methods=["POST"])
def asana_webhook():
    if "X-Hook-Secret" in request.headers:
        return jsonify({}), 200, {"X-Hook-Secret": request.headers["X-Hook-Secret"]}
    
    data = request.json
    
    if data and "events" in data:
        for event in data["events"]:
            event.get("resource", {}).get("gid")
            action = event.get("action")
            
            if action == "added" and event["resource"].get("resource_subtype") == "comment_added":
                comment_gid = event["resource"].get("gid")
                comment_url = f"https://app.asana.com/api/1.0/stories/{comment_gid}"
                headers = {
                    "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
                }
                comment_response = requests.get(comment_url, headers=headers)
                
                if comment_response.status_code == 200:
                    comment_data = comment_response.json()
                    comment_text = comment_data.get("data", {}).get("text", "No comment text found")
                    
                    client_info = fetch_client_data_by_task_id(event['parent']['gid'])
                    if client_info:
                        channel_id = client_info.get("slack_id")
                        if channel_id:
                            try:
                                app.client.chat_postMessage(
                                    channel=channel_id,
                                    text = f"Hi {client_info.get('client_name_short', 'there')}, here's the thumbnail we made for you!\n\n{comment_text}"
                                )
                            except SlackApiError as e:
                                print(f"Error posting message to Slack: {e.response['error']}")
                        else:
                            print("Could not find Slack channel ID.")
                    else:
                        print("Could not find client info for task.")
                else:
                    print(f"Failed to fetch comment: {comment_response.text}")
        
        return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "failure"}), 400

def fetch_client_data_by_task_id(task_id):
    response = supabase.table("clientbase").select("*").eq("current_task", task_id).execute()
    return response.data[0] if response.data else None

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(debug=True)