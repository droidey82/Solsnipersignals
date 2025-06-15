import os
import time
import requests
import json
import gspread
from datetime import datetime, timezone
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDS_FILE = "/etc/secrets/google_creds.json"  # Render secret file path
SPREADSHEET_NAME = "Sol Sniper Logs"

# === CONSTANTS ===
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"

# === TELEGRAM ===
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"📩 Telegram response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# === GOOGLE SHEETS ===
def log_to_google_sheets(row):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.append_row(row)
        print("✅ Logged to Google Sheets")
    except Exception as e:
        print(f"❌ Google Sheets logging failed: {e}")

# === DEXSCREENER SCANNER ===
def check_dexscreener():
    print(f"\n🧑‍🚀 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        response = requests.get(DEXSCREENER_URL, timeout=10)
        if response.status_code != 200 or not response.text.strip():
            raise ValueError(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")

        data = response.json()
        pairs = data.get("pairs", [])
        print(f"🔍 Found {len(pairs)} tokens to evaluate")

        for pair in pairs:
            token_name = pair.get("baseToken", {}).get("name", "")
            token_symbol = pair.get("baseToken", {}).get("symbol", "")
            url = pair.get("url", "")
            liq = float(pair.get("liquidity", {}).get("usd", 0))
            holders = int(pair.get("holders", 0))
            fully_diluted_valuation = pair.get("fdv", {})
            top_holders = pair.get("topHolders", {})
            volume_change = float(pair.get("volumeChange", {}).get("m5", 0))
            lp_locked = pair.get("liquidity", {}).get("lockStatus", "") == "locked"

            if lp_locked and liq >= 10000 and volume_change >= 20 and holders <= 200 and top_holders.get("max", 0) <= 5:
                alert = f"🚨 <b>{token_name} ({token_symbol})</b>\n💧 LP Locked\n📈 Volume +{volume_change:.1f}%\n👥 Holders: {holders}\n🔗 <a href='{url}'>View on DexScreener</a>"
                send_telegram_alert(alert)
                log_to_google_sheets([
                    datetime.now(timezone.utc).isoformat(),
                    token_name,
                    token_symbol,
                    liq,
                    holders,
                    volume_change,
                    url
                ])

    except Exception as e:
        print(f"❌ Error fetching or scanning DexScreener data: {e}")

if __name__ == "__main__":
    startup_msg = "\u2705 <b>Bot started and ready to snipe</b>\n<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders \u2264 5% and min $10k liquidity</i>"
    send_telegram_alert(startup_msg)

    while True:
        check_dexscreener()
        print("✅ Finished scan, sleeping 5m")
        time.sleep(300)
