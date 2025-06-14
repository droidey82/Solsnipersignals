import os import requests import time from datetime import datetime from dotenv import load_dotenv

Load environment variables

load_dotenv() TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

API endpoints

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana" BIRDEYE_BASE_URL = "https://public-api.birdeye.so/public/token/" HEADERS = {"X-API-KEY": BIRDEYE_API_KEY}

Safety thresholds

MIN_LIQUIDITY_USD = 10000 MIN_VOLUME_5M = 15000 MAX_HOLDER_PERCENTAGE = 5 SEEN_TOKENS = set()

def send_telegram_alert(message): url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" payload = { "chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML" } try: response = requests.post(url, json=payload) print(f"Telegram response: {response.status_code}, {response.text}") return response.status_code == 200 except Exception as e: print(f"❌ Telegram send failed: {e}") return False

def token_is_safe(token_address): try: resp = requests.get(f"{BIRDEYE_BASE_URL}{token_address}/holders", headers=HEADERS) data = resp.json() if not data.get("data"): return False top_holders = data["data"][:5] for holder in top_holders: if holder["share"] > MAX_HOLDER_PERCENTAGE: return False return True except Exception as e: print(f"❌ Error in token_is_safe: {e}") return False

def check_dexscreener(): try: print(f"[{datetime.utcnow()}] Scanning Solana pairs...") response = requests.get(DEXSCREENER_API_URL) pairs = response.json().get("pairs", [])

