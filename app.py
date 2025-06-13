from flask import Flask, request
import requests
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

app = Flask(__name__)

# Telegram credentials
TELEGRAM_BOT_TOKEN = "7695990250:AAFdo9m1kbXYtmQMK0j0qcv65LPb8lMIA7k"
TELEGRAM_CHAT_ID = "-1002847073811"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Load Google credentials from environment variable
google_creds_json = os.environ.get("GOOGLE_CREDS")
google_creds_dict = json.loads(google_creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)

gc = gspread.authorize(credentials)
sheet = gc.open("SolSniperSignals Tracker").sheet1  # Make sure this name matches your sheet

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    if not data:
        return {"error": "No JSON received"}, 400

    token = data.get("token", "Unknown")
    price = float(data.get("price", 0))
    volume = data.get("volume", "N/A")

    tp_price = round(price * 1.15, 4)  # 15% target profit

    # Send Telegram message
    message = (
        f"🚀 <b>New Token Alert</b>\n"
        f"Token: <code>{token}</code>\n"
        f"Price: <code>{price}</code>\n"
        f"Volume: <code>{volume}</code>\n"
        f"TP Target: <code>{tp_price}</code>"
    )
    telegram_response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

    # Log to Google Sheets
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, token, price, volume, tp_price, ""])

    if telegram_response.status_code == 200:
        return {"status": "sent"}, 200
    else:
        return {
            "error": "Telegram error",
            "status": telegram_response.status_code,
            "details": telegram_response.json()
        }, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
