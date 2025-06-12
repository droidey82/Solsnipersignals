from flask import Flask, request
import os
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return 'Sol Sniper Signals Bot is Live!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received alert:", data)

    message = f"🚀 Token: {data.get('token_name', 'Unknown')}\nPrice: {data.get('price', 'N/A')}"
    telegram_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    payload = {
        'chat_id': os.environ['TELEGRAM_CHANNEL_ID'],
        'text': message
    }
    requests.post(telegram_url, json=payload)

    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run()
