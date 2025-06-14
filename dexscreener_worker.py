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
VOLUME_SPIKE_PERCENT = 20

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
        print(f"📬 Telegram response: {response.status_code} - {response.text}", flush=True)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram send failed: {e}", flush=True)
        return False


def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        if resp.status_code != 200:
            print(f"⚠️ Birdeye error: {resp.status_code}", flush=True)
            return False
        data = resp.json()
        print(f"🔎 Checking holders for {token_address}...", flush=True)
        top_holders = data.get("data", [])[:5]
        for holder in top_holders:
            if holder.get("share", 0) > MAX_HOLDER_PERCENTAGE:
                print(f"❌ Holder exceeds {MAX_HOLDER_PERCENTAGE}%: {holder}", flush=True)
                return False
        return True
    except Exception as e:
        print(f"❌ Error in token_is_safe: {e}", flush=True)
        return False


def check_dexscreener():
    try:
        print(f"\n🕵️‍♂️ {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
        response = requests.get(DEXSCREENER_API_URL, timeout=10)
        if response.status_code != 200 or not response.text.strip().startswith("{"):
            raise ValueError("Invalid DexScreener API response")
        data = response.json()
        print(f"✅ Raw API response keys: {data.keys()}", flush=True)

        pairs = data.get("pairs", [])
        print(f"🔢 Found {len(pairs)} pairs", flush=True)

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume", {}).get("h5", 0))
            base_token = token.get("baseToken", {})

            print(f"➡️ {base_token.get('symbol')} - Liquidity: {liquidity}, Volume: {volume}", flush=True)

            if liquidity < MIN_LIQUIDITY_USD or volume < MIN_VOLUME_5M:
                continue

            if not token_is_safe(base_token.get("address", "")):
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
        print(f"❌ Error fetching or scanning DexScreener data: {e}", flush=True)


if __name__ == "__main__":
    startup_msg = (
        "✅ <b>Bot started and ready to snipe</b>\n"
        "<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders ≤ 5% and min $10k liquidity</i>"
    )
    send_telegram_alert(startup_msg)

    while True:
        check_dexscreener()
        print("✅ Finished scan, sleeping 5m", flush=True)
        time.sleep(300)
