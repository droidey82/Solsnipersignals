import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHANNEL_ID")
MIN_LIQUIDITY_USD = 10000
MIN_VOLUME_USD = 15000
DELAY_SECONDS = 300  # 5 minutes

def get_new_pairs():
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("pairs", [])
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Failed to fetch pairs: {e}")
        return []

def passes_filters(pair):
    try:
        liquidity = float(pair["liquidity"]["usd"])
        volume = float(pair["volume"]["h24"])
        if liquidity >= MIN_LIQUIDITY_USD and volume >= MIN_VOLUME_USD:
            return True
    except Exception as e:
        print(f"Error in passes_filters: {e}")
    return False

def format_alert(pair):
    try:
        name = pair["baseToken"]["name"]
        symbol = pair["baseToken"]["symbol"]
        url = pair["url"]
        liquidity = round(float(pair["liquidity"]["usd"]), 2)
        volume = round(float(pair["volume"]["h24"]), 2)
        price = pair["priceUsd"]

        return (
            f"🚀 <b>New Token Alert</b>\n"
            f"<b>Name:</b> {name} ({symbol})\n"
            f"<b>Price:</b> ${price}\n"
            f"<b>Liquidity:</b> ${liquidity:,}\n"
            f"<b>Volume (24h):</b> ${volume:,}\n"
            f"<a href=\"{url}\">📊 View Chart</a>"
        )
    except Exception as e:
        return f"❌ Error formatting alert: {e}"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload)
        if not response.ok:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

def main():
    print(f"[{datetime.now()}] ✅ Dexscreener worker started")
    seen = set()

    while True:
        try:
            pairs = get_new_pairs()
            for pair in pairs:
                pair_id = pair["pairAddress"]
                if pair_id not in seen and passes_filters(pair):
                    msg = format_alert(pair)
                    send_telegram_alert(msg)
                    seen.add(pair_id)
        except Exception as e:
            print(f"Unexpected error: {e}")
        time.sleep(DELAY_SECONDS)

if __name__ == "__main__":
    main()