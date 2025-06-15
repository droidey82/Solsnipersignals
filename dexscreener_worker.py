
import os
import time
import requests
import datetime
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

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
        print(f"ðŸ“¨ Telegram response: {response.status_code} - {response.text}", flush=True)
    except Exception as e:
        print(f"ðŸš¨ Error sending Telegram alert: {e}", flush=True)

def log_to_google_sheets(data_row):
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row(data_row)
        print("âœ… Logged to Google Sheets", flush=True)
    except Exception as e:
        print(f"âš ï¸ Google Sheets logging error: {e}", flush=True)

def fetch_solana_pairs():
    url = "https://api.dexscreener.com/latest/dex/pairs?chainId=solana"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"âŒ Error fetching or scanning DexScreener data: {e}", flush=True)
        return None

def check_dexscreener():
    print(f"\nðŸ§  {datetime.datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    data = fetch_solana_pairs()
    if not data or "pairs" not in data:
        print("ðŸš« No valid pairs data found.", flush=True)
        return

    filtered = []
    for pair in data["pairs"]:
        try:
            liq_usd = float(pair["liquidity"]["usd"])
            holders = pair.get("fdv", 0)
            top_holders = pair.get("topHolders", [])[:1]
            locked = "uncx" in str(pair.get("liquidity", {})).lower() or "mudra" in str(pair.get("liquidity", {})).lower()

            if locked and liq_usd >= 10000:
                msg = f"ðŸš€ Token: {pair['baseToken']['name']} ({pair['baseToken']['symbol']})\nLP Locked: Yes\nLiquidity: ${liq_usd:,.0f}\nURL: {pair['url']}"
                send_telegram_alert(msg)
                log_to_google_sheets([datetime.datetime.utcnow().isoformat(), pair['baseToken']['name'], pair['baseToken']['symbol'], liq_usd, pair['url']])
                filtered.append(msg)
        except Exception as e:
            print(f"Error parsing pair: {e}", flush=True)

    print(f"âœ… Scan complete. {len(filtered)} tokens passed filters.", flush=True)

# Notify startup
startup_msg = "âœ… <b>Bot started and ready to snipe</b>\n<i>Monitoring Solana tokens every 5 minutes with LP lock and min $10k liquidity</i>"
send_telegram_alert(startup_msg)

if __name__ == "__main__":
    while True:
        check_dexscreener()
        print("âœ… Finished scan, sleeping 5m\n", flush=True)
        time.sleep(300)