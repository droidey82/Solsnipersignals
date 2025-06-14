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
VOLUME_SPIKE_THRESHOLD = 20  # % increase in 5m volume

SEEN_TOKENS = set()


def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload)
        print(f"Telegram response: {res.status_code} - {res.text}", flush=True)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Telegram send failed: {e}", flush=True)
        return False


def is_token_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        top_holders = data.get("data", [])[:5]
        for holder in top_holders:
            if holder.get("share", 0) > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"⚠️ Holder safety check failed: {e}", flush=True)
        return False


def has_locked_liquidity(token):
    lp_info = token.get("liquidity", {})
    return lp_info.get("locked") is True


def has_volume_spike(token):
    try:
        volume_change = float(token.get("volumeChange", {}).get("h5", 0))
        return volume_change >= VOLUME_SPIKE_THRESHOLD
    except:
        return False


def check_dexscreener():
    print(f"\n🕵️ {datetime.utcnow()} - Scanning Solana tokens...\n", flush=True)
    try:
        res = requests.get(DEXSCREENER_API_URL)
        data = res.json()
        pairs = data.get("pairs", [])
        print(f"✅ Raw API response keys: {list(data.keys())}", flush=True)

        for token in pairs:
            address = token.get("pairAddress")
            if address in SEEN_TOKENS:
                continue

            name = token.get("baseToken", {}).get("name", "?")
            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume_5m = float(token.get("volume", {}).get("h5", 0))

            print(f"🔎 {name} | LP ${liquidity:,.0f} | 5m Vol ${volume_5m:,.0f}", flush=True)

            if liquidity < MIN_LIQUIDITY_USD:
                continue
            if not is_token_safe(token.get("baseToken", {}).get("address", "")):
                continue
            if not has_locked_liquidity(token):
                continue
            if not has_volume_spike(token):
                continue

            SEEN_TOKENS.add(address)

            message = (
                f"<b>🚨 New Solana Token</b>\n"
                f"<b>Name:</b> {name}\n"
                f"<b>Symbol:</b> {token.get('baseToken', {}).get('symbol', '-') }\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume_5m:,.0f}\n"
                f"<b>Dex:</b> {token.get('dexId')}\n"
                f"<b>Pair:</b> <a href='{token.get('url')}'>View</a>"
            )
            send_telegram_alert(message)

    except Exception as e:
        print(f"❌ Error fetching or scanning DexScreener data: {e}", flush=True)
    print("✅