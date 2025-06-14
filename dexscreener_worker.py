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
MAX_HOLDER_PERCENTAGE = 5
VOLUME_SPIKE_THRESHOLD = 1.2  # 20% spike
SEEN_TOKENS = set()

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        print("📤 Sending Telegram message...")
        response = requests.post(url, json=payload)
        print("✅ Response:", response.status_code)
        return response.status_code == 200
    except Exception as e:
        print("❌ Telegram send failed:", e)
        return False

def token_is_safe(token_address):
    try:
        print(f"🔎 Checking holders for {token_address}")
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        if not data.get("data"):
            return False
        top_holders = data["data"][:5]
        for holder in top_holders:
            if holder["share"] > MAX_HOLDER_PERCENTAGE:
                print(f"🚫 Holder exceeds {MAX_HOLDER_PERCENTAGE}%: {holder['share']:.2f}%")
                return False
        return True
    except Exception as e:
        print("❌ Error in token_is_safe:", e)
        return False

def lp_is_locked_or_burned(token_data):
    try:
        lp_lock = token_data.get("liquidity", {}).get("lock")
        return lp_lock in ["locked", "burned"]
    except:
        return False

def check_dexscreener():
    try:
        print(f"[{datetime.utcnow()}] 🔍 Scanning Solana tokens...")
        response = requests.get(DEXSCREENER_API_URL)
        pairs = response.json().get("pairs", [])

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            vol_5m = float(token.get("volume", {}).get("h5", 0))
            vol_15m = float(token.get("volume", {}).get("h15", 1))  # Avoid division by 0

            if liquidity < MIN_LIQUIDITY_USD:
                continue
            if vol_5m / vol_15m < VOLUME_SPIKE_THRESHOLD:
                continue
            if not lp_is_locked_or_burned(token):
                continue
            if not token_is_safe(token.get("baseToken", {}).get("address", "")):
                continue

            SEEN_TOKENS.add(address)

            message = (
                "<b>🚀 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {token.get('baseToken', {}).get('name', 'Unknown')}\n"
                f"<b>Symbol:</b> {token.get('baseToken', {}).get('symbol', '-')}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${vol_5m:,.0f}\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print("❌ Error in check_dexscreener:", e)

# ✅ Startup message
startup_msg = (
    "\u2705 <b>Bot started and ready to snipe</b>\n"
    "<i>Scanning Solana tokens every 5 minutes with filters:</i>\n"
    "• LP locked/burned\n"
    "• Top holders ≤ 5%\n"
    "• Liquidity ≥ $10k\n"
    "• 5m volume spike ≥ 20%"
)
send_telegram_alert(startup_msg)

# 🔁 Run loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)