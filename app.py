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
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sol Sniper Logs")

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/google_creds.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    print("❌ Google Sheets setup failed:", str(e))
    sheet = None  # fallback in case of sheet issues

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    try:
        data = request.json
        if not data:
            return {"error": "No JSON received"}, 400

        token = data.get("token", "Unknown")
        price = data.get("price", "N/A")
        volume = data.get("volume", "N/A")

        message = f"🚀 <b>New Token Alert</b>\nToken: <code>{token}</code>\nPrice: <code>{price}</code>\nVolume: <code>{volume}</code>"

        tg_response = requests.post(TELEGRAM_API_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })

        sheet_status = "Skipped"
        if sheet:
            try:
                sheet.append_row([token, price, volume])
                sheet_status = "Logged to sheet"
            except Exception as e:
                sheet_status = f"Logging failed: {str(e)}"

        return {
            "status": "Alert processed",
            "telegram_status": tg_response.status_code,
            "telegram_response": tg_response.text,
            "sheet_status": sheet_status
        }, 200

    except Exception as e:
        print("❌ Alert error:", str(e))
        return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)