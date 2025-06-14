import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"
BIRDEYE_BASE_URL = "https://public-api.birdeye.so/public/token/"
HEADERS = {"X-API-KEY": BIRDEYE_API_KEY}

SEEN_TOKENS = set()

Minimums

MIN_LIQUIDITY_USD = 5000
MIN_VOLUME_5M = 5000
MAX_HOLDER_PERCENTAGE = 15
# Token safety checks

def token_is_safe(token_address):
    try:
        resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS)
        data = resp.json()
        if not data.get("data"):
            return False
        top_holders = data["data"]["list"]
        for holder in top_holders:
            if holder["share"] > MAX_HOLDER_PERCENTAGE:
                return False
        return True
    except Exception as e:
        print(f"Error in token_is_safe: {e}")
        return False

def send_telegram_alert(message): url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" payload = { "chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML" } try: response = requests.post(url, json=payload) return response.status_code == 200 except Exception as e: print(f"Telegram send failed: {e}") return False

def check_dexscreener(): try: response = requests.get(DEXSCREENER_API_URL) pairs = response.json().get("pairs", []) for token in pairs: address = token.get("pairAddress") if address in SEEN_TOKENS: continue

liquidity = float(token.get("liquidity", {}).get("usd", 0))
        volume = float(token.get("volume", {}).get("h5", 0))
        price = token.get("priceUsd", "0")
        symbol = token.get("baseToken", {}).get("symbol", "")
        name = token.get("baseToken", {}).get("name", "")

        if liquidity >= MIN_LIQUIDITY_USD and volume >= MIN_VOLUME_5M:
            if token_is_safe(address):
                message = f"🚀 <b>New Token Alert</b>\n<b>Name:</b> {name}\n<b>Symbol:</b> {symbol}\n<b>Price:</b> ${price}\n<b>Liquidity:</b> ${liquidity:,.0f}\n<b>Volume 5m:</b> ${volume:,.0f}\n<a href='https://dexscreener.com/solana/{address}'>View on Dexscreener</a>"
                send_telegram_alert(message)
                SEEN_TOKENS.add(address)
except Exception as e:
    print(f"Error in check_dexscreener: {e}")

if name == "main": while True: check_dexscreener() time.sleep(300)

