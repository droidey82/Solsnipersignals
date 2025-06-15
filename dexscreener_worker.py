import sys
import os
import requests
import json
import time
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
from telegram import Bot

print("✅ Starting SolSniper worker")
load_dotenv()

# --- Telegram ---
def send_telegram_alert(msg):
    try:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise Exception("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing")
        bot = Bot(token=token)
        response = bot.send_message(chat_id=chat_id, text=msg).to_dict()
        print("📤 Telegram alert sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# --- Google Sheets logging ---
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

# --- DexScreener scan ---
def scan_tokens():
    print(f"\n🧑‍🚀 {datetime.utcnow()} - Scanning Solana tokens...")
    url = "https://api.dexscreener.io/latest/dex/pairs?chainId=solana"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    for attempt in range(3):
        response = requests.get(url, headers=headers)
        print(f"📡 Status: {response.status_code}")
        print(f"🧾 Content-Type: {response.headers.get('Content-Type')}")
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            break
        elif response.status_code == 429:
            print(f"⚠️ Rate limit hit (attempt {attempt+1}/3) — sleeping 60s")
            time.sleep(60)
        else:
            print("❌ Unexpected response:", response.status_code)
            print("🔎 Preview:", response.text[:300])
            if attempt == 2:
                print("❌ DexScreener still failing after retries.")
                return
    else:
        return

    try:
        data = response.json()
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        return

    pairs = data.get("pairs", [])
    if not pairs:
        print("🔴 No pairs returned.")
        return

    matches = []
    for pair in pairs:
        if pair.get("chainId") != "solana":
            continue
        try:
            base = pair.get("baseToken", {})
            liquidity = float(pair.get("liquidity", {}).get("usd", 0))
            volume = float(pair.get("volume", {}).get("h24", 0))
            locked = pair.get("liquidity", {}).get("locked", False)
            burned = pair.get("liquidity", {}).get("burned", False)
            holders_ok = all(h.get("share", 0) <= 5.0 for h in pair.get("holders", []))

            if liquidity >= 10000 and volume >= 10000 and holders_ok and (locked or burned):
                msg = (
                    f"🔥 {base.get('name')} ({base.get('symbol')})\n"
                    f"Liquidity: ${liquidity:,.0f}\n"
                    f"Volume (24h): ${volume:,.0f}\n"
                    f"LP Locked: {locked}\nLP Burned: {burned}\n"
                    f"URL: {pair.get('url')}"
                )
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(),
                    base.get('name'), base.get('symbol'),
                    liquidity, volume, locked, burned,
                    pair.get('url')
                ])
                matches.append(msg)
        except Exception as e:
            print(f"⚠️ Pair parsing error: {e}")
    print(f"✅ Scan done. {len(matches)} tokens matched.")

# --- Run loop ---
if __name__ == "__main__":
    send_telegram_alert("✅ Bot started. Scanning Solana tokens every 5 minutes.\nFilters: LP locked/burned, holders ≤5%, $10k+ liquidity & volume")
    while True:
        scan_tokens()
        print("⏳ Sleeping 5 min...")
        time.sleep(300)