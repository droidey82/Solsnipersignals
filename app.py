from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def home():
    return "SolSniperSignals bot is live."

@app.route("/alert", methods=["POST"])
def alert():
    try:
        data = request.get_json(force=True)
        token = data.get("token", "Unknown")
        price = data.get("price", "N/A")
        volume = data.get("volume", "N/A")

        text = f"🚀 *New Token Alert!*\nToken: {token}\nPrice: {price}\nVolume: {volume}"

        response = requests.post(TELEGRAM_URL, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })

        if response.ok:
            return {"status": "sent"}, 200
        else:
            return {
                "error": "Telegram error",
                "status": response.status_code,
                "details": response.text
            }, 500

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
