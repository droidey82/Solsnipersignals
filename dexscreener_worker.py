import sys
print("Using Python version:", sys.version)

import os
import requests
import time
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
from telegram import Bot

# Load .env variables
load_dotenv()

# Telegram setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Google Sheets setup
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

# Telegram alert
def send_telegram_alert(msg):
    try:
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print("📤 Telegram alert sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# DexScreener scan
def scan_tokens():
    print(f"\n🔍 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://api.dexscreener.com/latest/dex/pairs?chainId=solana"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"📱 Status: {response.status_code}")

        if response.status_code == 429:
            print("⚠️ Rate limited. Sleeping 60s...")
            time.sleep(60)
            response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Unexpected response: {response.status_code}")

        if "application/json" not in response.headers.get("Content-Type", ""):
            raise Exception("Expected JSON response.")

        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            print("🔴 No tokens found.")
            return

        count = 0
        for pair in pairs:
            if pair.get("chainId") != "solana":
                continue

            try:
                base = pair["baseToken"]
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                locked = pair.get("liquidity", {}).get("locked", False)
                burned = pair.get("liquidity", {}).get("burned", False)
                holders = pair.get("holders", [])
                holders_ok = all(float(h.get("share", 0)) <= 5.0 for h in holders)

                if liquidity >= 10000 and volume >= 10000 and (locked or burned) and holders_ok:
                    msg = (
                        f"🔥 {base['name']} ({base['symbol']})\n"
                        f"Liquidity: ${liquidity:,.0f}\n"
                        f"Volume: ${volume:,.0f}\n"
                        f"LP Locked: {locked} | Burned: {burned}\n"
                        f"URL: {pair['url']}"
                    )
                    send_telegram_alert(msg)
                    log_to_google_sheets([
                        datetime.utcnow().isoformat(),
                        base['name'],
                        base['symbol'],
                        liquidity,
                        volume,
                        locked,
                        burned,
                        pair['url']
                    ])
                    count += 1

            except Exception as e:
                print(f"⚠️ Token parse error: {e}")

        print(f"✅ Scan complete. {count} tokens passed filters.")

    except Exception as e:
        print(f"🚨 DexScreener error: {e}")

# --- Main loop ---
if __name__ == "__main__":
    send_telegram_alert("✅ Bot started. Monitoring Solana tokens...")
    time.sleep(10)
    while True:
        scan_tokens()
        print("⏳ Sleeping 5 min...\n", flush=True)
        time.sleep(300)