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
MAX_HOLDER_PERCENTAGE = 5
MIN_VOLUME_SPIKE_PERCENT = 20

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
        url = f"{BIRDEYE_BASE_URL}{token_address}/holders"
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        top_holders = data.get("data", [])[:5]
        for holder in top_holders:
            if holder.get("share", 0) > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"Error checking holders: {e}")
        return False

def lp_is_locked(token):
    try:
        return token.get("liquidity", {}).get("lockStatus", "") == "locked"
    except:
        return False

def volume_spike_is_high(token):
    try:
        change = float(token.get("priceChange", {}).get("h5", 0))
        return abs(change) >= MIN_VOLUME_SPIKE_PERCENT
    except:
        return False

def check_dexscreener():
    try:
        print(f"\n🔍 {datetime.utcnow()} - Scanning Solana tokens...\n")
        response = requests.get(DEXSCREENER_API_URL)
        data = response.json()

        print(f"🔧 Raw API response keys: {list(data.keys())}")
        pairs = data.get("pairs", [])
        print(f"✅ Retrieved {len(pairs)} token pairs from DexScreener")

        for token in pairs:
            pair_address = token.get("pairAddress")
            if not pair_address or pair_address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            if liquidity < MIN_LIQUIDITY_USD:
                continue

            if not lp_is_locked(token):
                continue

            if not volume_spike_is_high(token):
                continue

            base_address = token.get("baseToken", {}).get("address", "")
            if not token_is_safe(base_address):
                continue

            SEEN_TOKENS.add(pair_address)

            name = token.get("baseToken", {}).get("name", "Unknown")
            symbol = token.get("baseToken", {}).get("symbol", "???")
            volume = float(token.get("volume", {}).get("h5", 0))
            dex = token.get("dexId", "Unknown")
            url = token.get("url", "#")

            message = (
                f"<b>🚀 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {name}\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {dex}\n"
                f"<b>Pair:</b> <a href='{url}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"❌ Error fetching DexScreener data: {e}")

# ✅ Send startup alert
startup_message = (
    "✅ Bot started and ready to snipe\n"
    "<i>Monitoring Solana tokens every 5 minutes with LP lock, "
    "top holders ≤ 5% and min $10k liquidity</i>"
)
send_telegram_alert(startup_message)

# 🔁 Run loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)