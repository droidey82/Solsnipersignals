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
REQUIRED_LP_LOCKED = True
SEEN_TOKENS = set()


def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        if not response.ok:
            print(f"[❌] Telegram error: {response.text}")
        return response.ok
    except Exception as e:
        print(f"[❌] Telegram send failed: {e}")
        return False


def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json().get("data", [])
        if not data:
            return False
        for holder in data[:5]:
            if holder.get("share", 0) > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"[⚠️] Error in token_is_safe: {e}")
        return False


def lp_is_locked(token_data):
    try:
        return token_data.get("liquidity", {}).get("lock", "").lower() == "locked"
    except Exception as e:
        print(f"[⚠️] LP lock check error: {e}")
        return False


def check_dexscreener():
    try:
        print(f"\n⏱️  {datetime.utcnow()} - Scanning Solana pairs...\n")
        response = requests.get(DEXSCREENER_API_URL)
        pairs = response.json().get("pairs", [])

        for token in pairs:
            address = token.get("pairAddress")
            name = token.get("baseToken", {}).get("name", "Unknown")
            symbol = token.get("baseToken", {}).get("symbol", "-")
            print(f"🔎 Checking {name} ({symbol})")

            if address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume", {}).get("h5", 0))

            if liquidity < MIN_LIQUIDITY_USD or volume < MIN_VOLUME_5M:
                continue

            if REQUIRED_LP_LOCKED and not lp_is_locked(token):
                continue

            base_token_address = token.get("baseToken", {}).get("address", "")
            if not token_is_safe(base_token_address):
                continue

            SEEN_TOKENS.add(address)
            message = (
                f"<b>🚀 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {name}\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"[❌] Error fetching from DexScreener: {e}")


# ✅ Send a Telegram message on startup
startup_msg = "<b>✅ Bot started and ready to snipe</b>\n<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders ≤ 5%, and min $10k liquidity</i>"
send_telegram_alert(startup_msg)

# 🔁 Run loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)  # every 5 minutes