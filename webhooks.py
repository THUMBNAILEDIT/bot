import os
import json
import requests
from flask import request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.errors import SlackApiError

from config import SLACK_BOT_TOKEN, SLACK_API_URL, ASANA_ADMIN_ID
from database import fetch_client_data, fetch_client_data_by_task_id, update_client_thread_mapping
from asana_utils import move_task_to_archive
from commands import app

handler = SlackRequestHandler(app)

def asana_webhook():
    if "X-Hook-Secret" in request.headers:
        return jsonify({}), 200, {"X-Hook-Secret": request.headers["X-Hook-Secret"]}

    data = request.json
    if data and "events" in data:
        for event in data["events"]:
            if event.get("action") == "added" and event["resource"].get("resource_subtype") == "comment_added":
                task_id = event["parent"]["gid"]
                comment_gid = event["resource"]["gid"]

                comment_url = f"https://app.asana.com/api/1.0/stories/{comment_gid}"
                headers = {"Authorization": f"Bearer {os.getenv('ASANA_ACCESS_TOKEN')}"}
                comment_response = requests.get(comment_url, headers=headers)
                if comment_response.status_code != 200:
                    print("Failed to fetch comment:", comment_response.text)
                    continue

                comment_data = comment_response.json().get("data", {})
                comment_text = comment_data.get("text", "")
                comment_author_id = comment_data.get("created_by", {}).get("gid")
                # print(f"Comment fetched: {comment_text}, Author ID: {comment_author_id}")

                if comment_author_id == ASANA_ADMIN_ID:
                    # print(f"Skipping comment by bot account: {comment_text}")
                    continue

                client_info = fetch_client_data_by_task_id(task_id)
                if not client_info:
                    print(f"No client info found for task ID: {task_id}")
                    continue

                thread_mappings = client_info.get("thread_mappings") or {}
                thread_ts = next((k for k, v in thread_mappings.items() if v == task_id), None)

                if not thread_ts:
                    response = app.client.chat_postMessage(
                        channel=client_info["slack_id"],
                        text=f"Hi {client_info.get('client_name_short', 'there')}, here's the thumbnail we made for you!\n\n{comment_text}",
                        blocks=[
                            {
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": f"Hi {client_info.get('client_name_short', 'there')}, here's the thumbnail we made for you!\n\n{comment_text}"},
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "accept_work"},
                                    {"type": "button", "text": {"type": "plain_text", "text": "Request Revisions"}, "action_id": "request_revisions"},
                                ],
                            },
                        ],
                    )
                    thread_ts = response["ts"]
                    # print(f"Created new thread: {thread_ts}")

                    update_client_thread_mapping(client_info["slack_id"], thread_ts, task_id)

                else:
                    app.client.chat_postMessage(
                        channel=client_info["slack_id"],
                        text=comment_text,
                        thread_ts=thread_ts,
                        blocks=[
                            {
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": comment_text},
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "accept_work"},
                                    {"type": "button", "text": {"type": "plain_text", "text": "Request Revisions"}, "action_id": "request_revisions"},
                                ],
                            },
                        ],
                    )

        return jsonify({"status": "success"}), 200

    return jsonify({"status": "failure"}), 400

def slack_actions():
    payload = request.form["payload"]
    data = json.loads(payload)

    action = data.get("actions")[0]
    channel_id = data["channel"]["id"]
    response_url = data["response_url"]
    message_ts = data.get("message", {}).get("ts")

    if action["action_id"] == "accept_work":
        client_info = fetch_client_data(channel_id)
        if client_info:
            task_id = client_info.get('current_task')
            if task_id:
                move_task_to_archive(task_id)

                requests.post(
                    response_url,
                    json={
                        "replace_original": True,
                        "text": "The task has been approved and archived. Thank you!"
                    }
                )
            else:
                print("No task ID found to archive")
        else:
            print("Could not find client info")
        return jsonify({"status": "success"})

    elif action["action_id"] == "request_revisions":
        client_info = fetch_client_data(channel_id)
        if client_info:
            task_id = client_info.get("current_task")
            if task_id:
                thread_ts = message_ts
                
                thread_message = requests.post(
                    f"{SLACK_API_URL}/chat.postMessage",
                    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                    json={
                        "channel": channel_id,
                        "text": "Please provide your revisions below.",
                        "thread_ts": thread_ts,
                    },
                )
                if thread_message.status_code == 200:
                    # print("Saving mapping:", thread_ts, "->", task_id)
                    update_client_thread_mapping(channel_id, thread_ts, task_id)
                    requests.post(
                        response_url,
                        json={
                            "replace_original": True,
                            "text": "Your revision request has been noted. Please provide details in the thread."
                        }
                    )
                    return jsonify({"status": "success"})
                else:
                    print("Failed to post message in thread:", thread_message.text)
                    return jsonify({"status": "failure", "error": "Failed to post message in thread"}), 500
            else:
                print("No current task found for this client.")
        else:
            print("Client information not found.")

    return jsonify({"status": "failure", "message": "Action not handled properly"}), 400

@app.event("message")
def handle_thread_messages(event, say):
    # print("Received message event:", event)

    if "thread_ts" in event:
        thread_ts = event["thread_ts"]
        channel_id = event["channel"]
        user_message = event.get("text", "")

        client_info = fetch_client_data(channel_id)
        if client_info:
            thread_mappings = client_info.get("thread_mappings", {})
            # print("Thread mappings in database:", thread_mappings)
            # print("Thread TS in event:", thread_ts)
            # print("Available thread_ts in mappings:", list(thread_mappings.keys()))

            task_id = thread_mappings.get(thread_ts)

            if task_id:
                headers = {
                    "Authorization": f"Bearer {os.getenv('ASANA_ACCESS_TOKEN')}",
                    "Content-Type": "application/json"
                }
                comment_url = f"https://app.asana.com/api/1.0/tasks/{task_id}/stories"
                data = {"data": {"text": user_message}}
                response = requests.post(comment_url, headers=headers, json=data)

                if response.status_code == 201:
                    say(text="Your revision has been sent to the designer!", thread_ts=thread_ts)
                else:
                    say(text="Failed to send your revision. Please try again.", thread_ts=thread_ts)
            else:
                say(text="Could not find a corresponding Asana task for this thread.", thread_ts=thread_ts)
        else:
            say(text="Could not find client information.", thread_ts=thread_ts)