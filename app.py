from flask import Flask, request
import requests
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# Telegram configuration
TELEGRAM_BOT_TOKEN = "7695990250:AAFdo9m1kbXYtmQMK0j0qcv65LPb8lMIA7k"
TELEGRAM_CHAT_ID = "-1002847073811"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Google Sheets setup
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDS")
google_creds_dict = json.loads(GOOGLE_CREDS)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("SolSniperSignals").sheet1  # ✅ Update to match your sheet name

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    if not data:
        return {"error": "No JSON received"}, 400

    token = data.get("token", "Unknown")
    price = data.get("price", "N/A")
    volume = data.get("volume", "N/A")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Format Telegram message
    message = f"🚀 <b>New Token Alert</b>\nToken: <code>{token}</code>\nPrice: <code>{price}</code>\nVolume: <code>{volume}</code>"

    # Send to Telegram
    response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

    # Log to Google Sheets
    try:
        sheet.append_row([timestamp, token, price, volume, "", "", ""])
    except Exception as e:
        return {"error": "Google Sheets error", "details": str(e)}, 500

    # Return success/failure
    if response.status_code == 200:
        return {"status": "sent"}, 200
    else:
        return {
            "error": "Telegram error",
            "status": response.status_code,
            "details": response.json()
        }, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)