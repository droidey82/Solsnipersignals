from flask import Flask, request
import os
import requests

app = Flask(__name__)

# Telegram setup
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    if not data:
        return {"error": "No JSON received"}, 400

    # Format the alert message
    token_name = data.get("token", "Unknown Token")
    price = data.get("price", "N/A")
    volume = data.get("volume", "N/A")
    telegram_message = f"🚀 *New Alert:*\nToken: {token_name}\nPrice: {price}\nVolume: {volume}"

    # Send to Telegram
    response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_message,
        "parse_mode": "Markdown"
    })

    # Debug log
    print("Telegram API response:", response.status_code, response.text)

    if response.status_code == 200:
        return {"status": "sent"}, 200
    else:
        return {"error": f"Telegram error: {response.text}"}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
