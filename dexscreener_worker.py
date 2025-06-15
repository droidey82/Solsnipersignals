import sys
print("Using Python version:", sys.version)
import os
import requests
import json
import time
from datetime import datetime, timezone
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
import telegram

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_telegram_alert(msg):
    try:
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(f"ðŸ“¤ Telegram response: {response}")
    except Exception as e:
        print(f"âŒ Telegram error: {e}")

def log_to_google_sheets(row):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "/etc/secrets/GOOGLE_CREDS_JSON"
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Sol Sniper Logs").sheet1
        sheet.append_row(row)
    except Exception as e:
        print(f"âŒ Google Sheets error: {e}")

def scan_tokens():
    print(f"\nðŸ§‘â€ðŸš€ {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://api.dexscreener.io/latest/dex/pairs/solana"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")

        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            print("ðŸ”´ No valid pairs data found.")
            return

        filtered = []
        for pair in pairs:
            try:
                base_token = pair["baseToken"]
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                holders_ok = all(float(h.get("share", 0)) <= 5.0 for h in pair.get("holders", []))
                if liquidity >= 10000 and holders_ok and pair.get("liquidity", {}).get("locked", True):
                    msg = f"ðŸ”¥ {base_token['name']} ({base_token['symbol']})\nLiquidity: ${liquidity:,.0f}\nURL: {pair['url']}"
                    send_telegram_alert(msg)
                    log_to_google_sheets([
                        datetime.utcnow().isoformat(),
                        base_token['name'],
                        base_token['symbol'],
                        liquidity,
                        pair['url']
                    ])
                    filtered.append(msg)
            except Exception as e:
                print(f"Error parsing pair: {e}", flush=True)
        print(f"âœ… Scan complete. {len(filtered)} tokens passed filters.", flush=True)
    except Exception as e:
        print(f"ðŸš¨ Error fetching or scanning DexScreener data: {e}")

if __name__ == "__main__":
    send_telegram_alert("âœ… Bot started and ready to snipe\nMonitoring Solana tokens every 5 minutes with LP lock, top holders â‰¤5%, and min $10k liquidity")
    while True:
        scan_tokens()
        print("â³ Finished scan, sleeping 5m", flush=True)
        time.sleep(300)