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
MIN_VOLUME_SPIKE_PCT = 20

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
        print(f"Telegram status: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
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
                print(f"❌ Top holder exceeds {MAX_HOLDER_PERCENTAGE}%: {holder['share']}")
                return False
        return True
    except Exception as e:
        print(f"Holder check failed: {e}")
        return False

def is_lp_locked(token):
    info = token.get("liquidity", {}).get("lock", "")
    return "locked" in str(info).lower() or "burned" in str(info).lower()

def check_dexscreener():
    print(f"\n🔍 {datetime.utcnow()} - Scanning Solana pairs...\n")
    try:
        response = requests.get(DEXSCREENER_API_URL)
        data = response.json()
print(f"✅ Raw API response keys: {data.keys()}")
pairs = data.get("pairs", [])
print(f"✅ Retrieved {len(pairs)} pairs from DexScreener")

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume_5m = float(token.get("volume", {}).get("h5", 0))
            volume_15m = float(token.get("volume", {}).get("h15", 1)) or 1  # avoid div by 0
            volume_spike_pct = ((volume_5m - (volume_15m / 3)) / (volume_15m / 3)) * 100

            print(f"🔸 {token.get('baseToken', {}).get('symbol', '-')} - ${liquidity} liquidity / ${volume_5m} 5m vol / {volume_spike_pct:.1f}% spike")

            if liquidity < MIN_LIQUIDITY_USD:
                print("⛔ Skipped: Insufficient liquidity")
                continue
            if volume_5m < MIN_VOLUME_5M:
                print("⛔ Skipped: Low volume")
                continue
            if volume_spike_pct < MIN_VOLUME_SPIKE_PCT:
                print("⛔ Skipped: No significant volume spike")
                continue
            if not is_lp_locked(token):
                print("⛔ Skipped: LP not locked")
                continue
            if not token_is_safe(token.get("baseToken", {}).get("address", "")):
                print("⛔ Skipped: Unsafe holder concentration")
                continue

            SEEN_TOKENS.add(address)
            message = (
                f"<b>🚨 New Solana Token Detected</b>\n"
                f"<b>Name:</b> {token.get('baseToken', {}).get('name', '-')}\n"
                f"<b>Symbol:</b> {token.get('baseToken', {}).get('symbol', '-')}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume_5m:,.0f}\n"
                f"<b>Spike:</b> {volume_spike_pct:.1f}%\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"❌ Error scanning DexScreener: {e}")

# ✅ Startup notice
send_telegram_alert(
    "✅ Bot started and ready to snipe\n"
    "Monitoring Solana tokens every 5 minutes with LP lock, top holders ≤ 5%, "
    "volume ≥ $15k, and 20% spike detection"
)

# 🔁 Main loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)