import os
import json
import requests
import time
from datetime import datetime
import telegram

# === Load secrets ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or open("/etc/secrets/TELEGRAM_TOKEN").read().strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or open("/etc/secrets/TELEGRAM_CHAT_ID").read().strip()

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# === DexScreener Solana feed ===
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"

def send_startup_message():
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🟢 SolSniper worker started at " + datetime.utcnow().strftime('%H:%M:%S UTC'))

def fetch_tokens():
    try:
        response = requests.get(DEXSCREENER_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('pairs', [])
    except Exception as e:
        print(f"[ERROR] Fetch failed: {e}")
        return []

def passes_filters(token):
    reasons = []
    
    try:
        volume = float(token.get("volume", {}).get("h24", 0))  # 24h volume
        name = token.get("baseToken", {}).get("name", "UNKNOWN")
        holders = 100  # Placeholder – replace if real holder data available
        lp_locked = True  # Placeholder – replace if LP lock logic exists

        if volume < 10000:
            reasons.append(f"Low volume (${volume:,.0f})")
        if not lp_locked:
            reasons.append("LP not locked")
        if holders < 10:
            reasons.append("Low holder count")

        return (len(reasons) == 0, reasons)
    except Exception as e:
        return (False, [f"Exception: {str(e)}"])

def main_loop():
    send_startup_message()

    while True:
        print("\n[INFO] Fetching at", datetime.utcnow().strftime('%H:%M:%S UTC'))
        tokens = fetch_tokens()
        print(f"[INFO] Retrieved {len(tokens)} tokens")

        valid_count = 0

        for token in tokens:
            name = token.get("baseToken", {}).get("name", "UNKNOWN")
            symbol = token.get("baseToken", {}).get("symbol", "")
            url = token.get("url", "")

            passed, reasons = passes_filters(token)

            if passed:
                print(f"[✅] {name} passed filters — sending alert.")
                message = f"🚀 *{name} ({symbol})* looks promising!\n🔗 {url}"
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
                valid_count += 1
            else:
                print(f"[❌] {name} excluded: {'; '.join(reasons)}")

        if valid_count == 0:
            print("[INFO] No valid tokens this round.")

        time.sleep(60)

if __name__ == "__main__":
    main_loop()