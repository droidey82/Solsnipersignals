from flask import Flask, request
import requests
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Telegram setup
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/google_creds.json", scope)
client = gspread.authorize(creds)

# Open your shared sheet
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "SolSniperSignals")
sheet = client.open(SHEET_NAME).sheet1

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

    message = f"🚀 <b>New Token Alert</b>\nToken: <code>{token}</code>\nPrice: <code>{price}</code>\nVolume: <code>{volume}</code>"

    # Send to Telegram
    tg_response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

    # Log to Google Sheets
    try:
        sheet.append_row([token, price, volume])
    except Exception as e:
        print("Sheet logging failed:", str(e))

    if tg_response.status_code == 200:
        return {"status": "Alert sent & logged"}, 200
    else:
        return {
            "error": "Telegram error",
            "status": tg_response.status_code,
            "details": tg_response.json()
        }, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)