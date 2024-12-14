from flask import Flask, request
from webhooks import handler, asana_webhook, slack_actions

flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/asana-webhook", methods=["POST"])
def asana_webhook_route():
    return asana_webhook()

@flask_app.route("/slack-actions", methods=["POST"])
def slack_actions_route():
    return slack_actions()

if __name__ == "__main__":
    flask_app.run(debug=True)