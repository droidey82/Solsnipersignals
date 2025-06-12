
from flask import Flask, request
import os
import requests
import time

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

@app.route('/')
def index():
    return "Sol Sniper Signals Bot is live!"

@app.route('/alert', methods=['POST'])
def alert():
    data = request.get_json()
    if not data or "token" not in data or data["token"] != os.getenv("WEBHOOK_TOKEN"):
        return {"error": "Unauthorized"}, 401

    symbol = data.get("symbol", "Unknown Token")
    price = data.get("price", "N/A")
    volume = data.get("volume", "N/A")
    url = data.get("url", "")
    message = f"ðŸš¨ *New Trade Signal: {symbol}*
Price: ${price}
Volume: ${volume}
[View on DexScreener]({url})"

    send_telegram_message(message)
    return {"status": "ok"}, 200

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
