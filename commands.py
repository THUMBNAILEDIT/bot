from slack_bolt import App
from database import fetch_client_data, update_client_credits, update_client_current_task
from asana_utils import create_asana_task, register_webhook_for_task
from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

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

    update_client_credits(channel_id, client_info.get('current_credits', 0) - 1)

    task_name = f"Request from {client_info['client_name_short']}"
    task_notes = f"""
ORDER INFORMATION
Order type: YouTube Thumbnail
Deliverables:
    • 1920 x 1080 image (.JPG)
    • Project file (.PSD)

CLIENT INFORMATION
Client: {client_info.get('client_name_full', 'Unknown')} 
Client's channel: {client_info.get('client_channel_name', 'Unknown')} ({client_info.get('client_channel_link', 'Unknown')})

STYLE
Client's preferences: {client_info.get('client_preferences', 'Unknown')}
Thumbnail examples: {client_info.get('client_thumbnail_examples', 'Unknown')}

TASK DESCRIPTION
Video Description: {description}
"""
    task_id = create_asana_task(task_name, task_notes)
    
    if task_id:
        update_client_current_task(channel_id, task_id)
        register_webhook_for_task(task_id)

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