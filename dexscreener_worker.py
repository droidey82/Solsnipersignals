import requests
import time
import json
from datetime import datetime
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import gspread
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SHEET_NAME = "Sol Sniper Logs"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print("📨 Telegram response:", response.status_code, "-", response.text[:500])
    except Exception as e:
        print("❌ Telegram error:", e)

def log_to_google_sheets(row):
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row(row)
        print("✅ Logged to Google Sheets.")
    except Exception as e:
        print("❌ Google Sheets error:", e)

def check_dexscreener():
    print(f"\n🧑‍🚀 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        url = "https://api.dexscreener.io/latest/dex/pairs/solana"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")
        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            print("🛑 No valid pairs data found.")
            return
        for pair in pairs:
            try:
                base_token = pair["baseToken"]
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                is_locked = pair.get("liquidity", {}).get("lockStatus") in ["locked", "burned"]

                if liquidity >= 10000 and is_locked:
                    alert_msg = (
                        f"<b>🔥 Token Alert: {base_token['name']} ({base_token['symbol']})</b>\n"
                        f"<i>Liquidity:</i> ${liquidity:,.0f}\n"
                        f"<i>24h Volume:</i> ${volume:,.0f}"
                    )
                    send_telegram_alert(alert_msg)
                    log_to_google_sheets([
                        str(datetime.utcnow()),
                        base_token["name"],
                        base_token["symbol"],
                        f"${liquidity:,.0f}",
                        f"${volume:,.0f}"
                    ])
            except Exception as inner_e:
                print("⚠️ Error processing pair:", inner_e)
    except Exception as e:
        print("❌ Error fetching or scanning DexScreener data:", e)

if __name__ == "__main__":
    send_telegram_alert("✅ Bot started and ready to snipe\n<i>Monitoring Solana tokens every 5 minutes with LP lock and min $10k liquidity</i>")
    while True:
        check_dexscreener()
        print("✅ Finished scan, sleeping 5m\n")
        time.sleep(300)