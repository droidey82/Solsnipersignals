from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

@app.route("/")
def home():
    return "✅ SolSniperSignals Dexscreener bot is live."

@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Ping received."}), 200

@app.route("/test-alert", methods=["GET"])
def test_alert():
    message = (
        "🚀 <b>Test Signal</b>\n"
        "Token: <code>SOL/USDC</code>\n"
        "Price: <code>1.23</code>\n"
        "Volume: <code>9999</code>\n"
        "Market Cap: <code>123k</code>\n"
        "#Test"
    )

    telegram_response = requests.post(TELEGRAM_API_URL, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

    if telegram_response.ok:
        return jsonify({"status": "Alert sent", "telegram_response": telegram_response.json()}), 200
    else:
        return jsonify({
            "status": "Telegram failed",
            "code": telegram_response.status_code,
            "response": telegram_response.text
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)