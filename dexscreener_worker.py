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

MIN_LIQUIDITY_USD = 10000
MIN_VOLUME_5M = 15000
MAX_HOLDER_PERCENTAGE = 5

SEEN_TOKENS = set()

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

def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        if not data.get("data"):
            return False
        top_holders = data["data"][:5]
        for holder in top_holders:
            if holder.get("share", 0) > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"Error in token_is_safe: {e}")
        return False

def check_dexscreener():
    try:
        print(f"[{datetime.utcnow()}] Scanning Solana pairs...")
        response = requests.get(DEXSCREENER_API_URL)
        pairs = response.json().get("pairs", [])

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume", {}).get("h5", 0))

            if liquidity < MIN_LIQUIDITY_USD or volume < MIN_VOLUME_5M:
                continue

            base_token = token.get("baseToken", {})
            token_address = base_token.get("address", "")
            if not token_address or not token_is_safe(token_address):
                continue

            SEEN_TOKENS.add(address)

            message = (
                f"<b>🚀 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {base_token.get('name', 'Unknown')}\n"
                f"<b>Symbol:</b> {base_token.get('symbol', '-')}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)  # every 5 minutes
# TEMPORARY TEST ALERT
send_telegram_alert(
    "<b>🚀 Test Alert</b>\n"
    "<b>Name:</b> Example Token\n"
    "<b>Symbol:</b> EXM\n"
    "<b>Liquidity:</b> $123,456\n"
    "<b>5m Volume:</b> $12,345\n"
    "<b>Dex:</b> Raydium\n"
    "<b>Pair:</b> <a href='https://dexscreener.com/solana/example'>View</a>"
)