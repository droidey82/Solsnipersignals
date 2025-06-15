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

# --- Send Telegram Alert ---
def send_telegram_alert(msg):
    try:
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            raise Exception("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        bot = Bot(token=TELEGRAM_TOKEN)
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(f"\U0001F4E4 Telegram response: {response}")
    except Exception as e:
        print(f"\u274C Telegram error: {e}")

# --- Log to Google Sheets ---
def log_to_google_sheets(row):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "/etc/secrets/GOOGLE_CREDS_JSON"
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Sol Sniper Logs").sheet1
        sheet.append_row(row)
    except Exception as e:
        print(f"\u274C Google Sheets error: {e}")

# --- Scan DexScreener for Solana tokens ---
def scan_tokens():
    print(f"\n\U0001F9D1\u200D\U0001F4BB {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://api.dexscreener.io/latest/dex/pairs?chainId=solana"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    max_retries = 3
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        print(f"\U0001F4F1 Status: {response.status_code}")

        print("\U0001F50D Content-Type:", response.headers.get("Content-Type"))
        print("\U0001F50E Response preview:", response.text[:100])

        if response.status_code == 200:
            break
        elif response.status_code == 429:
            print(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}) — sleeping 60 sec")
            time.sleep(60)
        else:
            print(f"\u274C Unexpected response: {response.status_code}")
            time.sleep(3)
    else:
        print("❌ DexScreener still failing after retries.")
        return

    if "application/json" not in response.headers.get("Content-Type", ""):
        print("⚠️ DexScreener did not return JSON.")
        return

    data = response.json()
    pairs = data.get("pairs", [])
    if not pairs:
        print("🔴 No valid pairs data found.")
        return

    filtered = []
    for pair in pairs:
        if pair.get("chainId") != "solana":
            continue
        try:
            base_token = pair["baseToken"]
            liquidity = float(pair.get("liquidity", {}).get("usd", 0))
            volume = float(pair.get("volume", {}).get("h24", 0))
            is_lp_locked = pair.get("liquidity", {}).get("locked", False)
            is_lp_burned = pair.get("liquidity", {}).get("burned", False)
            holders_ok = all(float(h.get("share", 0)) <= 5.0 for h in pair.get("holders", []))

            if liquidity >= 10000 and volume >= 10000 and holders_ok and (is_lp_locked or is_lp_burned):
                msg = (
                    f"\U0001F525 {base_token['name']} ({base_token['symbol']})\n"
                    f"Liquidity: ${liquidity:,.0f}\n"
                    f"Volume (24h): ${volume:,.0f}\n"
                    f"LP Locked: {is_lp_locked}\nLP Burned: {is_lp_burned}\n"
                    f"URL: {pair['url']}"
                )
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(),
                    base_token['name'],
                    base_token['symbol'],
                    liquidity,
                    volume,
                    is_lp_locked,
                    is_lp_burned,
                    pair['url']
                ])
                filtered.append(msg)
        except Exception as e:
            print(f"Error parsing pair: {e}", flush=True)

    print(f"✅ Scan complete. {len(filtered)} tokens passed filters.", flush=True)

# --- Main loop ---
if __name__ == "__main__":
    try:
        print("\n⏳ Starting DexScreener Worker...")
        send_telegram_alert("✅ Bot started and ready to snipe\nMonitoring Solana tokens every 5 min with filters.")
        time.sleep(10)
        while True:
            scan_tokens()
            print("\u23F3 Sleeping 5 min...")
            time.sleep(300)
    except Exception as e:
        print(f"❌ Fatal error: {e}", flush=True)
        send_telegram_alert(f"❌ Dex bot crashed: {e}")
