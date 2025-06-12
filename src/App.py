from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return 'Sol Sniper Signals Bot is Live!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Basic print debug
    print("Received alert:", data)

    # Example Telegram logic
    import requests

    message = f"🚀 Token: {data.get('token_name', 'Unknown')}\nPrice: {data.get('price', 'N/A')}"

    telegram_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    payload = {
        'chat_id': os.environ['TELEGRAM_CHANNEL_ID'],
        'text': message
    }
    response = requests.post(telegram_url, json=payload)

    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run()
