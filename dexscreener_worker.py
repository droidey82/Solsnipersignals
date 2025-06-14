import requests import os import time from datetime import datetime from dotenv import load_dotenv

Load environment variables

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

Dexscreener API URL for Solana trending tokens

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"

Track processed tokens to avoid repeats

seen_tokens = set()

Filtering thresholds

MIN_VOLUME = 15000  # in USD MIN_LIQUIDITY = 10000  # in USD MIN_BURN_PERCENT = 90 REQUIRE_LP_LOCKED = True

def send_telegram_alert(token_data): message = ( f"🚨 <b>New Token Detected</b>\n" f"<b>Name:</b> {token_data['baseToken']['name']} ({token_data['baseToken']['symbol']})\n" f"<b>Price:</b> ${token_data['priceUsd']}\n" f"<b>Volume:</b> ${token_data['volume']['h5']}\n" f"<b>Liquidity:</b> ${token_data['liquidity']['usd']}\n" f"<b>DEX:</b> {token_data['dexId']}\n" f"<a href='{token_data['url']}'>📈 View on DexScreener</a>" )

requests.post(TELEGRAM_API_URL, json={
    "chat_id": TELEGRAM_CHAT_ID,
    "text": message,
    "parse_mode": "HTML",
    "disable_web_page_preview": False
})

def is_safe_token(token): try: volume = float(token['volume']['h5']) liquidity = float(token['liquidity']['usd']) burn_percent = float(token.get('burned', 0)) lp_locked = token.get('liquidityLocked', False)

if volume < MIN_VOLUME:
        return False
    if liquidity < MIN_LIQUIDITY:
        return False
    if REQUIRE_LP_LOCKED and not lp_locked:
        return False
    if burn_percent < MIN_BURN_PERCENT:
        return False

    return True
except:
    return False

def fetch_and_alert(): try: response = requests.get(DEXSCREENER_API_URL) tokens = response.json().get("pairs", [])

for token in tokens:
        pair_address = token.get("pairAddress")
        if pair_address in seen_tokens:
            continue

        if is_safe_token(token):
            send_telegram_alert(token)
            seen_tokens.add(pair_address)

except Exception as e:
    print("Error in fetch_and_alert:", str(e))

if name == "main": while True: fetch_and_alert() time.sleep(300)  # every 5 minutes

