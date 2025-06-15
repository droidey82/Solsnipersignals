import sys
print("Using Python version:", sys.version)

import os
import requests
import json
import time
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

def send_telegram_alert(msg):
    try:
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            raise Exception("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print("📤 Telegram alert sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def log_to_google_sheets(row):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "/etc/secrets/GOOGLE_CREDS_JSON"
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Sol Sniper Logs").sheet1
        sheet.append_row(row)
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")

def scan_tokens():
    print(f"\n🙍‍♂️ {datetime.utcnow()} - Scanning Solana tokens...")
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    for attempt in range(1, 4):
        response = requests.get(url, headers=headers)
        status = response.status_code
        print(f"📡 DexScreener status: {status}")

        if status == 200 and "application/json" in response.headers.get("Content-Type", ""):
            break
        elif status in [429, 404]:
            print(f"⚠️ Unexpected response: {status}. Sleeping {30 * attempt}s...")
            time.sleep(30 * attempt)
        else:
            print(f"❌ Unexpected content-type or error: {response.text[:100]}")
            return
    else:
        print("❌ DexScreener still failing after retries.")
        return

    try:
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        return

    if not pairs:
        print("🔴 No pairs found.")
        return

    filtered = []
    for pair in pairs:
        try:
            liquidity = float(pair.get("liquidity", {}).get("usd", 0))
            volume = float(pair.get("volume", {}).get("h24", 0))
            is_lp_locked = pair.get("liquidity", {}).get("locked", False)
            is_lp_burned = pair.get("liquidity", {}).get("burned", False)
            holders_ok = all(float(h.get("share", 0)) <= 5.0 for h in pair.get("holders", []))
            base_token = pair.get("baseToken", {})
            name = base_token.get("name", "Unknown")
            symbol = base_token.get("symbol", "N/A")

            if liquidity >= 10000 and volume >= 10000 and holders_ok and (is_lp_locked or is_lp_burned):
                msg = (
                    f"🔥 {name} ({symbol})\n"
                    f"Liquidity: ${liquidity:,.0f}\n"
                    f"Volume (24h): ${volume:,.0f}\n"
                    f"LP Locked: {is_lp_locked}, LP Burned: {is_lp_burned}\n"
                    f"URL: {pair.get('url', 'N/A')}"
                )
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(),
                    name,
                    symbol,
                    liquidity,
                    volume,
                    is_lp_locked,
                    is_lp_burned,
                    pair.get('url', '')
                ])
                filtered.append(msg)
        except Exception as e:
            print(f"⚠️ Error parsing token: {e}")

    print(f"✅ Scan complete. {len(filtered)} tokens matched filters.")

if __name__ == "__main__":
    send_telegram_alert("✅ SolSniper Bot running. Scanning tokens every 5 mins for LP lock/burn + holder filters.")
    time.sleep(10)
    while True:
        scan_tokens()
        print("⏳ Sleeping 5 mins...\n")
        time.sleep(300)