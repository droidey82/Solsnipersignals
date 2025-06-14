import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"
BIRDEYE_BASE_URL = "https://public-api.birdeye.so/public/token/"
HEADERS = {"X-API-KEY": BIRDEYE_API_KEY}

SEEN_TOKENS = set()

# Minimums
MIN_LIQUIDITY_USD = 10000
MIN_VOLUME_5M = 15000
MAX_HOLDER_PERCENTAGE = 5

# Telegram alert sender
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False

# Token safety check
def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        if not data.get("data"):
            return False
        top_holders = data["data"][:5]
        for holder in top_holders:
            if holder["share"] > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"Error in token_is_safe: {e}")
        return False

# Main scanner logic
def check_dexscreener():
    try:
        response = requests.get(DEXSCREENER_API_URL)
        pairs = response.json().get("pairs", [])

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            volume = float(token.get("volume", {}).get("h5", 0))
            liquidity = float(token.get("liquidity", {}).get("usd", 0))

            if volume < MIN_VOLUME_5M or liquidity < MIN_LIQUIDITY_USD:
                continue

            if not token_is_safe(address):
                continue

            SEEN_TOKENS.add(address)

            name = token.get("baseToken", {}).get("name", "Unknown")
            symbol = token.get("baseToken", {}).get("symbol", "")
            url = token.get("url", "")

            msg = f"<b>{name} ({symbol})</b>\nðŸ’§ Liquidity: ${liquidity:,.0f}\nðŸ“Š Volume (5m): ${volume:,.0f}\nðŸ”— <a href='{url}'>View on Dexscreener</a>"
            send_telegram_alert(msg)

    except Exception as e:
        print(f"Error in check_dexscreener: {e}")

# Run every 5 minutes
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)