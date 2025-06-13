from flask import Flask, request
import os
import requests

app = Flask(__name__)

# Telegram setup
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002847073811"  # <-- HARD-CODED channel ID to avoid 404
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    if not data:
        return {"error": "No JSON received"}, 400

    token_name = data.get("token", "Unknown Token")
    price = data.get("price", "N/A")
    volume = data.get("volume", "N/A")

    message = f"🚀 *New Alert:*\nToken: {token_name}\nPrice: {price}\nVolume: {volume}"

    response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

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
