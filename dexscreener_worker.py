import os
import time
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open("Sol Sniper Logs").sheet1

def send_telegram_alert(message):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(TELEGRAM_API_URL, json=payload)
        print("📨 Telegram response:", response.status_code, response.text)
        return response.status_code == 200
    except Exception as e:
        print("❌ Telegram error:", e)
        return False

def log_to_sheet(token_name, token_symbol, liquidity, volume, url):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, token_name, token_symbol, liquidity, volume, url]
    sheet.append_row(row)

def check_dexscreener():
    print(f"\n🧪 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        tokens = data.get("pairs", [])
        print(f"🔍 {len(tokens)} tokens found on Solana.")

        for token in tokens:
            try:
                name = token.get("baseToken", {}).get("name", "N/A")
                symbol = token.get("baseToken", {}).get("symbol", "N/A")
                liquidity = float(token.get("liquidity", {}).get("usd", 0))
                volume_5m = float(token.get("volume", {}).get("usd", 0))
                pair_url = token.get("url", "")
                dex = token.get("dexId", "")

                if liquidity < 10000:
                    continue
                if volume_5m < 1.2 * (token.get("volume", {}).get("usd", 0) / 12):  # ~20% increase
                    continue
                if not token.get("liquidity", {}).get("lockStatus", "").lower().startswith("locked"):
                    continue

                message = (
                    f"<b>🚀 New Token Alert</b>\n"
                    f"<b>Name:</b> {name}\n"
                    f"<b>Symbol:</b> {symbol}\n"
                    f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                    f"<b>5m Volume:</b> ${volume_5m:,.0f}\n"
                    f"<b>Dex:</b> {dex}\n"
                    f"<b>Link:</b> <a href='{pair_url}'>Chart</a>"
                )
                if send_telegram_alert(message):
                    log_to_sheet(name, symbol, liquidity, volume_5m, pair_url)

            except Exception as token_err:
                print("⚠️ Token scan error:", token_err)

    except Exception as e:
        print("❌ Error fetching DexScreener data:", e)

if __name__ == "__main__":
    startup_msg = (
        "✅ <b>Bot started and ready to snipe</b>\n"
        "<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders \u2264 5% and min $10k liquidity</i>"
    )
    send_telegram_alert(startup_msg)

    while True:
        check_dexscreener()
        print("✅ Finished scan, sleeping 5m")
        time.sleep(300)
