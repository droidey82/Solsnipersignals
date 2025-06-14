import requests
import time
import os
from datetime import datetime

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/solana"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

MIN_VOLUME = 15000  # Minimum 24h volume
MIN_LIQUIDITY = 10000  # Minimum liquidity
RSI_THRESHOLD = 70  # Optional placeholder for future

def send_telegram_alert(token_name, price_usd, volume_usd):
    message = (
        f"🚀 <b>New Token Alert</b>\n"
        f"<b>Token:</b> {token_name}\n"
        f"<b>Price:</b> ${price_usd:.6f}\n"
        f"<b>Volume:</b> ${int(volume_usd):,}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def fetch_and_filter_pairs():
    try:
        res = requests.get(DEXSCREENER_API)
        pairs = res.json().get("pairs", [])
        for p in pairs:
            try:
                token_name = p["baseToken"]["name"]
                price = float(p["priceUsd"])
                volume = float(p["volume"]["h24"])
                liquidity = float(p["liquidity"]["usd"])

                if volume > MIN_VOLUME and liquidity > MIN_LIQUIDITY:
                    send_telegram_alert(token_name, price, volume)
            except Exception as e:
                print(f"[!] Error parsing pair: {e}")
    except Exception as e:
        print(f"[!] Error fetching data: {e}")

if __name__ == "__main__":
    while True:
        print(f"[{datetime.now()}] Scanning Solana pairs...")
        fetch_and_filter_pairs()
        time.sleep(300)  # Run every 5 mins