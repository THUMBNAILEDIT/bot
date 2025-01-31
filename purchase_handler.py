import requests
from flask import request, jsonify
from database import supabase
import logging
import requests

MONOBANK_API_URL = "https://api.monobank.ua/api/merchant/invoice/create"
MONOBANK_API_KEY = "uwr-ibObJ9VYrqPKJa_mcyepvk-Og8g1vtc9WDeLBm7E"

def verify_access_token(access_token):
    if not access_token:
        return {"error": "AccessToken is required"}, 403

    response = supabase.table("clientbase").select("*").eq("access_token", access_token).execute()
    if not response.data:
        return {"error": f"AccessToken '{access_token}' not found"}, 403

    return {"message": "AccessToken is valid"}, 200

def send_invoice_to_monobank(total, access_token):
    try:
        monobank_payload = {
            "amount": int(total * 100),
            "merchantPaymInfo": {
                "destination": "Service Purchase",
                "reference": access_token
            }
        }
        headers = {"X-Token": MONOBANK_API_KEY}
        response = requests.post(MONOBANK_API_URL, json=monobank_payload, headers=headers)
        if response.status_code == 200:
            monobank_data = response.json()
            return {"payment_url": monobank_data.get("pageUrl")}, 200
        else:
            return {"error": "Failed to create invoice", "details": response.json()}, response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def calculate_credits(plan, total):
    if plan == "monthly":
        pricing_table = {
            240: 4, 456: 8, 648: 12, 816: 16, 960: 20,
            1080: 24, 1092: 28, 1248: 32, 1440: 40,
            1728: 48, 2016: 56, 1296: 36, 2592: 72, 3024: 84
        }
        return pricing_table.get(total, 0)
    elif plan == "annual":
        pricing_table = {
            2592: 4, 4925: 8, 6998: 12, 8813: 16, 10368: 20,
            11664: 24, 12701: 28, 13478: 32, 15552: 40,
            18662: 48, 21773: 56, 13997: 36, 23328: 60, 27994: 72, 32659: 84
        }
        return pricing_table.get(total, 0)
    elif plan == "onetime":
        pricing_table = {
            70: 1, 140: 2, 210: 3, 260: 4, 325: 5,
            390: 6, 455: 7, 480: 8, 540: 9, 600: 10,
        }
        return pricing_table.get(total, 0)
    else:
        return 0
    
def process_payment(data):
    try:
        payment_status = data.get("status")
        access_token = data.get("reference")
        total = data.get("amount")
        plan = data.get("plan")

        if not access_token or not total:
            return jsonify({"error": "Invalid webhook data"}), 400

        if payment_status == "success":
            response = supabase.table("clientbase").select("current_credits").eq("access_token", access_token).execute()
            if response.data:
                client = response.data[0]
                current_credits = client.get("current_credits", 0)
                new_credits = current_credits + calculate_credits(plan, total)
                supabase.table("clientbase").update({"current_credits": new_credits}).eq("access_token", access_token).execute()
                return jsonify({"message": "Credits updated successfully"}), 200

        return jsonify({"error": "Payment not successful or invalid status"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# def process_monobank_payment_webhook():
#     data = request.json
#     return process_payment(data)

def process_monobank_payment_webhook(data):
    try:
        payment_status = data.get("status")
        access_token = data.get("reference")
        total = data.get("amount")
        plan = data.get("plan")

        if not access_token or not total:
            return {"error": "Invalid webhook data"}, 400

        if payment_status == "success":
            response = supabase.table("clientbase").select("current_credits").eq("access_token", access_token).execute()
            if response.data:
                client = response.data[0]
                current_credits = client.get("current_credits", 0)
                new_credits = current_credits + calculate_credits(plan, total)
                supabase.table("clientbase").update({"current_credits": new_credits}).eq("access_token", access_token).execute()
                return {"message": "Credits updated successfully"}, 200

        return {"error": "Payment not successful or invalid status"}, 400
    except Exception as e:
        return {"error": str(e)}, 500

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://thumbnailed-it-slack-bot.onrender.com/monobank/webhook"

headers = {"X-Token": MONOBANK_API_KEY}
payload = {
    "webHookUrl": WEBHOOK_URL
}

response = requests.post("https://api.monobank.ua/api/merchant/invoice/webhook", json=payload, headers=headers)

if response.status_code == 200:
    logger.info("Webhook successfully set!")
else:
    logger.error(f"Failed to set webhook: {response.status_code}, Response: {response.text}")