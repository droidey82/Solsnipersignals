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
MIN_VOLUME_SPIKE_PCT = 20  # Optional: volume spike logic if needed

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
        print("✅ Telegram response:", response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False

def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        if not data.get("data"):
            print("⚠️ No holder data for token:", token_address)
            return False
        top_holders = data["data"][:5]
        for holder in top_holders:
            if holder["share"] > MAX_HOLDER_PERCENTAGE:
                print(f"❌ Rejected: Holder share {holder['share']}% > {MAX_HOLDER_PERCENTAGE}%")
                return False
        return True
    except Exception as e:
        print(f"❌ Error checking token safety: {e}")
        return False

def check_dexscreener():
    print(f"\n🕵️ {datetime.utcnow()} - Scanning Solana tokens...\n")
    try:
        response = requests.get(DEXSCREENER_API_URL)
        data = response.json()
        pairs = data.get("pairs", [])

        print(f"✅ Raw API response keys: {data.keys()} - Total pairs: {len(pairs)}")

        for token in pairs:
            address = token.get("pairAddress")
            name = token.get("baseToken", {}).get("name", "Unknown")
            symbol = token.get("baseToken", {}).get("symbol", "-")
            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume", {}).get("h5", 0))
            dex = token.get("dexId", "")
            url = token.get("url", "")
            base_token_address = token.get("baseToken", {}).get("address", "")

            print(f"🔎 {symbol} - ${liquidity:,.0f} liquidity / ${volume:,.0f} 5m volume")

            if address in SEEN_TOKENS:
                print("⏭ Already seen.")
                continue
            if liquidity < MIN_LIQUIDITY_USD:
                print(f"❌ Skipped: liquidity ${liquidity:,.0f} < ${MIN_LIQUIDITY_USD}")
                continue
            if volume < MIN_VOLUME_5M:
                print(f"❌ Skipped: volume ${volume:,.0f} < ${MIN_VOLUME_5M}")
                continue
            if not token.get("liquidity", {}).get("lockStatus", "").lower() == "locked":
                print("❌ Skipped: LP not locked")
                continue
            if not token_is_safe(base_token_address):
                print("❌ Skipped: holder check failed")
                continue

            SEEN_TOKENS.add(address)
            message = (
                f"<b>🚀 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {name}\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {dex}\n"
                f"<b>Pair:</b> <a href='{url}'>View</a>"
            )
            print(f"📢 Sending alert for {symbol}")
            send_telegram_alert(message)

    except Exception as e:
        print(f"❌ Error fetching data: {e}")

# ✅ Notify startup
send_telegram_alert(
    "✅ <b>Bot started and ready to snipe</b>\n"
    "<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders ≤ 5%, "
    f"liquidity ≥ ${MIN_LIQUIDITY_USD}, and 5m volume ≥ ${MIN_VOLUME_5M}</i>"
)

# 🔁 Run loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)  # every 5 minutes