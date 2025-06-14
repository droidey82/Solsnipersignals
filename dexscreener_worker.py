import os
import requests
import time
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" HEADERS = {"X-API-KEY": BIRDEYE_API_KEY}

MIN_VOLUME = 15000 MIN_LIQUIDITY = 10000 TOP_HOLDER_THRESHOLD = 0.80

SOLANA_TOKENS_URL = "https://public-api.birdeye.so/public/tokenlist?sort_by=volume_24h&chain=solana" HOLDERS_API = "https://public-api.birdeye.so/public/token/holders" TOKEN_INFO_API = "https://public-api.birdeye.so/public/token/"

def get_top_tokens(): try: r = requests.get(SOLANA_TOKENS_URL, headers=HEADERS) r.raise_for_status() tokens = r.json().get("data", []) return [t for t in tokens if t.get("liquidity") >= MIN_LIQUIDITY and t.get("volume_24h") >= MIN_VOLUME] except Exception as e: print(f"[ERROR] Fetching tokens: {e}") return []

def is_bundle(token_info): return token_info.get("is_lp") or token_info.get("lp_holders")

def is_mintable_or_owned(token_info): return token_info.get("can_mint", False) or not token_info.get("is_renounced", False)

def top_holders_safe(token_address): try: r = requests.get(f"{HOLDERS_API}?address={token_address}&limit=5", headers=HEADERS) holders = r.json().get("data", []) total_pct = sum(float(h.get("holding_percent", 0)) for h in holders) return total_pct <= (TOP_HOLDER_THRESHOLD * 100) except Exception as e: print(f"[WARN] Holder check failed: {e}") return False

def fetch_token_info(address): try: r = requests.get(f"{TOKEN_INFO_API}{address}?chain=solana", headers=HEADERS) return r.json().get("data", {}) except Exception as e: print(f"[ERROR] Token info fetch failed: {e}") return {}

def send_alert(token): msg = ( f"<b>🚨 A-Grade Solana Token Detected</b>\n" f"Name: <b>{token.get('name')}</b>\n" f"Symbol: <code>{token.get('symbol')}</code>\n" f"Volume 24h: <code>${int(token.get('volume_24h')):,}</code>\n" f"Liquidity: <code>${int(token.get('liquidity')):,}</code>\n" f"Link: https://dexscreener.com/solana/{token.get('address')}" ) try: requests.post(TELEGRAM_API_URL, json={ "chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML" }) print(f"[ALERT] Sent: {token.get('symbol')}") except Exception as e: print(f"[ERROR] Telegram send failed: {e}")

def run_scan(): print(f"[{datetime.utcnow()}] Scanning for A-grade tokens...") tokens = get_top_tokens() for token in tokens: address = token.get("address") info = fetch_token_info(address)

if is_bundle(info):
        continue
    if is_mintable_or_owned(info):
        continue
    if not top_holders_safe(address):
        continue

    send_alert(token)

if name == "main": while True: run_scan() time.sleep(300)

