import json
from flask import Flask, request, jsonify
from webhooks import handler, asana_webhook, slack_actions
from commands import app
from slack_bolt.adapter.flask import SlackRequestHandler

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    if request.content_type == "application/json":
        data = request.json
        print("Received Event:", data)
        
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")})
        
        if data.get("type") == "event_callback":
            event = data.get("event", {})
            print("Event Data:", event)
            return handler.handle(request)

    return jsonify({"error": "Unsupported Media Type"}), 415

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)

@flask_app.route("/asana-webhook", methods=["POST"])
def asana_webhook_route():
    return asana_webhook()

@flask_app.route("/slack-actions", methods=["POST"])
def slack_actions_route():
    return slack_actions()

if __name__ == "__main__":
    flask_app.run(debug=True)