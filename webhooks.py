import os
import json
import requests
from flask import request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.errors import SlackApiError

from config import SLACK_BOT_TOKEN, SLACK_API_URL
from database import fetch_client_data, fetch_client_data_by_task_id
from asana_utils import move_task_to_archive
from commands import app

handler = SlackRequestHandler(app)

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
                    "Authorization": f"Bearer {os.getenv('ASANA_ACCESS_TOKEN')}"
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
                                    text=f"Hi {client_info.get('client_name_short', 'there')}, here's the thumbnail we made for you!\n\n{comment_text}",
                                    blocks=[
                                        {
                                            "type": "section",
                                            "text": {
                                                "type": "mrkdwn",
                                                "text": f"Hi {client_info.get('client_name_short', 'there')}, here's the thumbnail we made for you!\n\n{comment_text}"
                                            }
                                        },
                                        {
                                            "type": "actions",
                                            "elements": [
                                                {
                                                    "type": "button",
                                                    "text": {
                                                        "type": "plain_text",
                                                        "text": "Accept"
                                                    },
                                                    "action_id": "accept_work"
                                                },
                                                {
                                                    "type": "button",
                                                    "text": {
                                                        "type": "plain_text",
                                                        "text": "Request Revisions"
                                                    },
                                                    "action_id": "request_revisions"
                                                }
                                            ]
                                        }
                                    ]
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

def slack_actions():
    payload = request.form["payload"]
    data = json.loads(payload)

    action = data.get("actions")[0]
    user_id = data["user"]["id"]
    response_url = data["response_url"]
    channel_id = data.get("channel", {}).get("id")
    message_ts = data.get("message", {}).get("ts")

    print(f"Payload received: {payload}")
    print(f"Message Timestamp (message_ts): {message_ts}")

    if action["action_id"] == "accept_work":
        client_info = fetch_client_data(channel_id)

        if client_info:
            task_id = client_info.get('current_task')

            if task_id:
                move_task_to_archive(task_id)
            else:
                print("Could not find task ID to archive")
        else:
            print("Could not find client info")

        requests.post(response_url, json={
            "replace_original": True,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Hi, here's the thumbnail we made for you!\n\nThe task is approved and archived!"
                    }
                }
            ]
        })
        return jsonify({"status": "success"}), 200

    elif action["action_id"] == "request_revisions":
        if channel_id and message_ts:
            response = requests.post(
                f"{SLACK_API_URL}/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                json={
                    "channel": channel_id,
                    "text": "You can now provide your revision details by replying in this thread.",
                    "thread_ts": message_ts,
                },
            )
            print(f"Slack API response for thread creation: {response.status_code} - {response.text}")
        else:
            print("Failed to get channel or message timestamp for thread creation.")

        requests.post(response_url, json={
            "replace_original": True,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Hi, here's the thumbnail we made for you!\n\nPlease provide revision details below."
                    }
                }
            ]
        })
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "failure"}), 400