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
        print(f"📤 Telegram response: {response}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

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
        print(f"❌ Google Sheets error: {e}")

# --- Scan DexScreener for Solana tokens ---
def scan_tokens():
    print(f"\n🙍‍♂️ {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://api.dexscreener.com/latest/dex/pairs?chainId=solana"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    max_retries = 3
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        print(f"📱 DexScreener status: {response.status_code}")

        print("🔎 Content-Type:", response.headers.get("Content-Type"))
        print("🔎 Response preview:", response.text[:300])

        if response.status_code == 200:
            break
        elif response.status_code == 429:
            print(f"⚠️ Rate limited (attempt {attempt + 1}/{max_retries}). Sleeping 60s...")
            time.sleep(60)
        else:
            raise Exception(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")
    else:
        raise Exception("DexScreener 429 persisted after retries.")

    if "application/json" not in response.headers.get("Content-Type", ""):
        print("⚠️ DexScreener did not return JSON.")
        raise Exception("Invalid content type — expected JSON.")

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
                    f"🔥 {base_token['name']} ({base_token['symbol']})\n"
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
    send_telegram_alert("✅ Bot started and ready to snipe\nMonitoring Solana tokens every 5 minutes with LP lock/burn, top holders ≤5%, min $10k liquidity & volume")
    time.sleep(15)  # Cooldown before first scan
    while True:
        scan_tokens()
        print("⏳ Finished scan, sleeping 5m", flush=True)
        time.sleep(300)