print("✅ SolSniper worker script booted")
import os
import json
import requests
import time
from datetime import datetime
import telegram

print("[BOOT] SolSniper worker script started")

# === Load secrets ===
try:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or open("/etc/secrets/TELEGRAM_TOKEN").read().strip()
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or open("/etc/secrets/TELEGRAM_CHAT_ID").read().strip()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    print("[BOOT] Telegram bot initialized")
except Exception as e:
    print("[ERROR] Failed to load Telegram config:", str(e))
    raise SystemExit(1)

# === Test Telegram Message ===
try:
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🟢 SolSniper worker script started at " + datetime.utcnow().strftime('%H:%M:%S UTC'))
    print("[BOOT] Telegram test message sent")
except Exception as e:
    print("[ERROR] Telegram message failed:", str(e))

# === DexScreener Solana feed ===
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"

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
        volume = float(token.get("volume", {}).get("h24", 0))
        name = token.get("baseToken", {}).get("name", "UNKNOWN")
        holders = 100  # Placeholder
        lp_locked = True  # Placeholder

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
                try:
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
                except Exception as e:
                    print(f"[ERROR] Failed to send alert for {name}: {e}")
                valid_count += 1
            else:
                print(f"[❌] {name} excluded: {'; '.join(reasons)}")

        if valid_count == 0:
            print("[INFO] No valid tokens this round.")

        time.sleep(60)

# === Safe start point ===
if __name__ == "__main__":
    try:
        print("[BOOT] Entering main loop...")
        main_loop()
    except Exception as e:
        print("[CRASH] Unhandled exception:", str(e))