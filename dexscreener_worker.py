
import os
import requests
import time
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEET_NAME = "Sol Sniper Logs"
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print("ðŸ“¬ Telegram response:", response.status_code, response.text[:100])
    except Exception as e:
        print("Telegram error:", e)

def log_to_google_sheets(row_data):
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        credentials = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(credentials)
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        sheet.append_row(row_data, value_input_option="USER_ENTERED")
        print("âœ… Logged to Google Sheets")
    except Exception as e:
        print("Google Sheets logging error:", e)

def check_dexscreener():
    print(f"\nðŸ§‘â€ðŸš€ {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs?chainId=solana"
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
                holders = base_token.get("holders", 0)
                lp_locked = pair.get("liquidity", {}).get("lock", False)

                if liquidity >= 10000 and lp_locked:
                    msg = f"<b>ðŸš€ New Token Alert</b>\n" \
                          f"<b>Name:</b> {base_token['name']}\n" \
                          f"<b>Symbol:</b> {base_token['symbol']}\n" \
                          f"<b>Liquidity:</b> ${liquidity:,.0f}\n" \
                          f"<b>URL:</b> {pair['url']}"
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
                print(f"Error parsing pair: {e}")
        print(f"âœ… Scan complete. {len(filtered)} tokens passed filters.", flush=True)
    except Exception as e:
        print(f"âŒ Error fetching or scanning DexScreener data: {e}")

# Send startup alert
startup_msg = "<b>âœ… Bot started and ready to snipe</b>\n<i>Monitoring Solana tokens every 5 minutes with LP lock and min $10k liquidity</i>"
send_telegram_alert(startup_msg)

# Main loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        print("â³ Finished scan, sleeping 5m\n", flush=True)
        time.sleep(300)