# from flask import request, jsonify
# import requests
# from logger import logger
# from config import SLACK_CLIENT_ID, SLACK_CLIENT_SECRET

# def handle_oauth_callback():
#     code = request.args.get("code")
#     if not code:
#         return "Error: authorization code is missing.", 400

#     response = requests.post("https://slack.com/api/oauth.v2.access", data={
#         "code": code,
#         "client_id": SLACK_CLIENT_ID,
#         "client_secret": SLACK_CLIENT_SECRET,
#     })

#     data = response.json()
#     if not data.get("ok"):
#         return f"Slack OAuth error: {data.get('error')}", 400

#     logger.info(f"OAuth token received: {data}")
#     return jsonify(data)

# from flask import request, jsonify, redirect
# import requests
# from database import save_team_to_database
# from logger import logger
# from config import SLACK_CLIENT_ID, SLACK_CLIENT_SECRET

# def handle_oauth_callback():
#     logger.info("OAuth callback triggered")
#     code = request.args.get("code")
#     if not code:
#         logger.error("Authorization code missing")
#         return "Error: Authorization code missing.", 400

#     response = requests.post("https://slack.com/api/oauth.v2.access", data={
#         "code": code,
#         "client_id": SLACK_CLIENT_ID,
#         "client_secret": SLACK_CLIENT_SECRET,
#     })

#     data = response.json()
#     if not data.get("ok"):
#         logger.error(f"OAuth error: {data.get('error')}")
#         return "OAuth authorization failed.", 400

#     access_token = data["access_token"]
#     team_id = data["team"]["id"]
#     team_name = data["team"]["name"]
#     bot_user_id = data["bot_user_id"]

#     try:
#         save_team_to_database(team_id, team_name, access_token, bot_user_id)
#         logger.info(f"Bot installed in team: {team_name} ({team_id})")
#     except Exception as e:
#         logger.error(f"Failed to save team to database: {e}")
#         return "Database save failed.", 500

#     return redirect("https://your-website.com/success")