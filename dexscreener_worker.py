import sys
print("Using Python version:", sys.version)

import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# --- Send Telegram Alert ---
def send_telegram_alert(msg):
    try:
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            raise Exception("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        bot = Bot(token=TELEGRAM_TOKEN)
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(f"\U0001F4E4 Telegram alert sent.")
    except Exception as e:
        print(f"\u274C Telegram error: {e}")

# --- Scan Solana tokens from Birdeye ---
def scan_tokens():
    print(f"\n\U0001F9D1‍\U0001F4BB {datetime.utcnow()} - Scanning Solana tokens...")
    url = "https://public-api.birdeye.so/public/tokenlist?chain=solana"
    headers = {
        "X-API-KEY": os.getenv("BIRDEYE_API_KEY"),
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"\U0001F4C3 Birdeye status: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Invalid Birdeye API response: {response.status_code} - {response.text[:100]}")

        data = response.json()
        tokens = data.get("data", [])

        if not tokens:
            print("\U0001F534 No tokens returned.")
            return

        print(f"\u2705 Retrieved {len(tokens)} tokens from Birdeye.")

    except Exception as e:
        print(f"\u274C Exception: {e}")

# --- Main ---
if __name__ == "__main__":
    try:
        print("\u2705 Script loaded and running.")
        send_telegram_alert("✅ Bot started. Monitoring Solana tokens with $10k+ liquidity & volume")
        time.sleep(10)
        while True:
            print("\U0001F501 Beginning token scan loop")
            scan_tokens()
            print("⏳ Scan complete. Sleeping 5 min...")
            time.sleep(300)
    except Exception as e:
        print(f"❌ CRASH: {e}")
