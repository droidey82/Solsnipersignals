from flask import Flask, request import requests import os import gspread from oauth2client.service_account import ServiceAccountCredentials from datetime import datetime

app = Flask(name)

Telegram config

TELEGRAM_BOT_TOKEN = "7695990250:AAFdo9m1kbXYtmQMK0j0qcv65LPb8lMIA7k" TELEGRAM_CHAT_ID = "-1002847073811" TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

Google Sheets config

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"] GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS")  # this must be a JSON string SPREADSHEET_NAME = "SolSniperSignals"  # must exactly match your sheet name

Load credentials from environment string

import json creds_dict = json.loads(GOOGLE_CREDS_JSON) credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE) client = gspread.authorize(credentials) sheet = client.open(SPREADSHEET_NAME).sheet1

@app.route("/", methods=["GET"]) def home(): return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"]) def alert(): data = request.json if not data: return {"error": "No JSON received"}, 400

token = data.get("token", "Unknown")
price = data.get("price", "N/A")
volume = data.get("volume", "N/A")

# Send Telegram message
message = f"\ud83d\ude80 <b>New Token Alert</b>\nToken: <code>{token}</code>\nPrice: <code>{price}</code>\nVolume: <code>{volume}</code>"
response = requests.post(TELEGRAM_API_URL, json={
    "chat_id": TELEGRAM_CHAT_ID,
    "text": message,
    "parse_mode": "HTML"
})

# Log to Google Sheets
try:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, token, price, volume, "", ""])
except Exception as e:
    print("Sheet logging failed:", e)

if response.status_code == 200:
    return {"status": "sent"}, 200
else:
    return {
        "error": "Telegram error",
        "status": response.status_code,
        "details": response.json()
    }, 500

if name == "main": port = int(os.environ.get("PORT", 5000)) app.run(host="0.0.0.0", port=port)

