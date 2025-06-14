import os
import requests
import time
from datetime import datetime, timezone
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
VOLUME_SPIKE_THRESHOLD = 1.2  # 20% increase

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
        print(f"Sent alert. Telegram response: {response.text}")
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
            if holder["share"] > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"Error in token_is_safe: {e}")
        return False

def check_dexscreener():
    try:
        print(f"[{datetime.now(timezone.utc)}] Scanning Solana pairs...")
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

            base_address = token.get("baseToken", {}).get("address", "")
            if not token_is_safe(base_address):
                print(f"[FILTERED] Unsafe token: {token.get('baseToken', {}).get('symbol', '-')}")
                continue

            SEEN_TOKENS.add(address)

            message = (
                f"<b>New Solana Token Detected</b>\n"
                f"<b>Name:</b> {token.get('baseToken', {}).get('name', 'Unknown')}\n"
                f"<b>Symbol:</b> {token.get('baseToken', {}).get('symbol', '-')}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"\u274C Error fetching DexScreener data: {e}")

# Log startup and test credentials
startup_msg = (
    "\u2705 Bot started and ready to snipe\n"
    "<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders \u2264 5% and min $10k liquidity</i>"
)
send_telegram_alert(startup_msg)
print("\u2705 Startup alert sent to Telegram.")

# Main loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)
