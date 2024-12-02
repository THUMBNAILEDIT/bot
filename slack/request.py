import os
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from dotenv import find_dotenv, load_dotenv
from flask import Flask, request

load_dotenv(find_dotenv())

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@app.command("/request")
def handle_request(ack, command):
    ack()
    description = command["text"]
    channel_id = command["channel_id"]
    app.client.chat_postMessage(channel=channel_id, text=f"*Thank you, your thumbnail request has been received! Here's the video description you provided:* '{description}'\n\n––––––––––––––––––––––––––––––––––––––––\n\nYou have *999/10* credits left. Have any questions? Please message *'/help'* to see the answers to the FAQ, or *'@Bot'* to tag our AI customer support assistant!\n\n*BUT DO NOT CONTACT THE MANAGER GODDAMNIT*")

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run()