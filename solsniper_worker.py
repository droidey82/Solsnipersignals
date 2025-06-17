import os
import json
import requests
import time
from datetime import datetime
import telegram

print("[BOOT] Starting SolSniper worker script...", flush=True)

# === Load from Render ENV Vars only ===
try:
    TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
    print("[BOOT] Environment variables loaded", flush=True)
except KeyError as e:
    print(f"[ERROR] Missing environment variable: {str(e)}", flush=True)
    raise SystemExit(1)

# === Setup Telegram Bot ===
try:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🟢 SolSniper worker script started at " + datetime.utcnow().strftime('%H:%M:%S UTC'))
    print("[BOOT] Telegram bot initialized and test message sent", flush=True)
except Exception as e:
    print("[ERROR] Telegram setup or message failed:", str(e), flush=True)

# === DexScreener API ===
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"

def fetch_tokens():
    try:
        response = requests.get(DEXSCREENER_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("pairs", [])
    except Exception as e:
        print("[ERROR] Failed to fetch tokens:", str(e), flush=True)
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
        print(f"\n[INFO] Fetching tokens at {datetime.utcnow().strftime('%H:%M:%S UTC')}", flush=True)
        tokens = fetch_tokens()
        print(f"[INFO] Retrieved {len(tokens)} tokens", flush=True)

        valid_count = 0

        for token in tokens:
            name = token.get("baseToken", {}).get("name", "UNKNOWN")
            symbol = token.get("baseToken", {}).get("symbol", "")
            url = token.get("url", "")

            passed, reasons = passes_filters(token)

            if passed:
                print(f"[✅] {name} passed filters — sending alert.", flush=True)
                message = f"🚀 *{name} ({symbol})* looks promising!\n🔗 {url}"
                try:
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
                except Exception as e:
                    print(f"[ERROR] Failed to send alert for {name}: {e}", flush=True)
                valid_count += 1
            else:
                print(f"[❌] {name} excluded: {'; '.join(reasons)}", flush=True)

        if valid_count == 0:
            print("[INFO] No valid tokens this round.", flush=True)

        time.sleep(60)

if __name__ == "__main__":
    try:
        print("[BOOT] Entering main loop...", flush=True)
        main_loop()
    except Exception as e:
        print("[CRASH] Unhandled exception:", str(e), flush=True)