import sys
import os
import requests
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

def send_telegram_alert(msg):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print("Telegram alert sent.")
    except Exception as e:
        print(f"Telegram error: {e}")

def log_to_google_sheets(row):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "/etc/secrets/GOOGLE_CREDS_JSON"
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Sol Sniper Logs").sheet1
        sheet.append_row(row)
    except Exception as e:
        print(f"Google Sheets error: {e}")

def scan_tokens():
    print(f"\n🙍‍♂️ {datetime.utcnow()} - Scanning Solana tokens...")
    url = "https://public-api.birdeye.so/public/tokenlist?sort_by=volume_h24&order=desc&offset=0&limit=50"
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"📘 Birdeye status: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Invalid Birdeye API response: {response.status_code} - {response.text[:100]}")

        data = response.json().get("data", [])
        filtered = []

        for token in data:
            try:
                liquidity = float(token.get("liquidity", 0))
                volume = float(token.get("volume_h24", 0))

                if liquidity >= 10000 and volume >= 10000:
                    msg = (
                        f"🔥 {token['name']} ({token['symbol']})\n"
                        f"Liquidity: ${liquidity:,.0f}\n"
                        f"Volume (24h): ${volume:,.0f}\n"
                        f"URL: https://birdeye.so/token/{token['address']}?chain=solana"
                    )
                    send_telegram_alert(msg)
                    log_to_google_sheets([
                        datetime.utcnow().isoformat(),
                        token['name'],
                        token['symbol'],
                        liquidity,
                        volume,
                        token['address']
                    ])
                    filtered.append(msg)
            except Exception as e:
                print(f"Error parsing token: {e}")

        print(f"✅ Scan complete. {len(filtered)} tokens passed filters.")

    except Exception as e:
        print(f"🚨 Exception: {e}")

if __name__ == "__main__":
    send_telegram_alert("✅ Birdeye bot is now live! Monitoring Solana tokens with $10k+ liquidity & volume")
    time.sleep(10)
    while True:
        scan_tokens()
        print("⏳ Sleeping 5 min...")
        time.sleep(300)
