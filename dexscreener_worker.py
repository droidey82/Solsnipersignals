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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

# --- Send Telegram Alert ---
def send_telegram_alert(msg):
    try:
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            raise Exception("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        bot = Bot(token=TELEGRAM_TOKEN)
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(f"\U0001f4e4 Telegram response: {response}")
    except Exception as e:
        print(f"\u274c Telegram error: {e}")

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
        print(f"\u274c Google Sheets error: {e}")

# --- Scan Birdeye for Solana tokens ---
def scan_tokens():
    print(f"\n\U0001f9cd‍♂️ {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://public-api.birdeye.so/public/tokenlist?sort_by=volume_h24_usd&sort_type=desc&limit=50&offset=0&chain=solana"
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(f"\U0001f4f1 Birdeye status: {response.status_code}")
    if response.status_code != 200:
        raise Exception(f"Invalid Birdeye API response: {response.status_code} - {response.text[:100]}")

    data = response.json()
    tokens = data.get("data", [])
    if not tokens:
        print("\U0001f534 No tokens returned.")
        return

    for token in tokens:
        try:
            name = token.get("name")
            symbol = token.get("symbol")
            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume_h24", 0))

            if liquidity >= 10000 and volume >= 10000:
                msg = (
                    f"\U0001f525 {name} ({symbol})\n"
                    f"Liquidity: ${liquidity:,.0f}\n"
                    f"Volume (24h): ${volume:,.0f}\n"
                    f"Birdeye: https://birdeye.so/token/{token['address']}?chain=solana"
                )
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(),
                    name,
                    symbol,
                    liquidity,
                    volume,
                    f"https://birdeye.so/token/{token['address']}?chain=solana"
                ])
        except Exception as e:
            print(f"Error processing token: {e}", flush=True)

    print("\u2705 Scan complete.\n", flush=True)

# --- Main loop ---
if __name__ == "__main__":
    send_telegram_alert("\u2705 Birdeye Bot Started - Monitoring Solana tokens with $10k+ liquidity & volume")
    time.sleep(10)
    while True:
        scan_tokens()
        print("\u23f3 Sleeping for 5 minutes...\n", flush=True)
        time.sleep(300)
