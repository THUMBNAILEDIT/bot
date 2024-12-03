import os
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from dotenv import find_dotenv, load_dotenv
from flask import Flask, request
from supabase import create_client, Client

load_dotenv(find_dotenv())

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

def fetch_client_data(channel_id: str):
    response = supabase.table("clientbase").select(
        "client_name_full, client_name_short, client_channel_name, client_channel_link, client_channel_description, client_preferences, client_thumbnail_examples, current_credits"
    ).eq("slack_id", channel_id).execute()
    return response.data[0] if response.data else None

@app.command("/request")
def handle_request(ack, command):
    ack()
    description = command["text"]
    channel_id = command["channel_id"]
    client_info = fetch_client_data(channel_id)
    
    if client_info:
        app.client.chat_postMessage(
            channel=channel_id,
            text=(
                f"*Thank you {client_info.get('client_name_short', ' ')}, your thumbnail request has been received!*\n\n"
                f"*Here's the video description you provided:* '{description}'\n\n"
                f"––––––––––––––––––––––––––––––––––––––––\n\n"
                f"You have *{client_info.get('current_credits', 'N/A')}/10* credits left. "
                f"Have any questions? Please message *'/help'* to see the FAQ or *'@Bot'* for support!"
            )
        )
    else:
        app.client.chat_postMessage(
            channel=channel_id,
            text="*Error:* We couldn't find your client info. Please ensure your Slack channel is registered."
        )

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run()