import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_test():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "🚨 Telegram credentials test successful!",
        "parse_mode": "HTML"
    }
    print("Sending test alert to Telegram...")
    print("Payload:", payload)
    response = requests.post(url, json=payload)
    print("Status:", response.status_code)
    print("Response:", response.text)

send_telegram_test()