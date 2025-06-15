import os
import requests
import json
import time
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Prepare Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_service_account_file(
    "/etc/secrets/google_creds.json", scope
)
sheets_service = build("sheets", "v4", credentials=creds)
sheet = sheets_service.spreadsheets()

def send_telegram_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"📲 Telegram response: {response.status_code} - {response.text}", flush=True)
    except Exception as e:
        print(f"Error sending Telegram message: {e}", flush=True)

def log_to_google_sheets(row):
    try:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": [row]}
        ).execute()
        print("✅ Logged to Google Sheets.", flush=True)
    except Exception as e:
        print(f"Error logging to Google Sheets: {e}", flush=True)

def fetch_and_filter_tokens():
    print(f"\n🤖 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    print(f"🔎 Using URL: {url}", flush=True)
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")

        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            print("🛑 No valid pairs data found.", flush=True)
            return

        filtered = []
        for pair in pairs:
            try:
                base_token = pair["baseToken"]
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                holders = int(pair.get("holders", 0))
                url = pair.get("url", "")
                top_holders = pair.get("topHolders", [])
                top_holder_percent = float(top_holders[0].get("percent", 100)) if top_holders else 100
                
                if pair.get("liquidity", {}).get("lock") not in ["locked", "burned"]:
                    continue

                if liquidity < 10000 or top_holder_percent > 5:
                    continue

                msg = f"🚀 <b>{base_token['name']} ({base_token['symbol']})</b>\nLiquidity: ${liquidity:,.0f}\nURL: {url}"
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(),
                    base_token["name"],
                    base_token["symbol"],
                    liquidity,
                    url
                ])
                filtered.append(msg)
            except Exception as e:
                print(f"Error parsing pair: {e}", flush=True)

        print(f"\n✅ Scan complete. {len(filtered)} tokens passed filters.", flush=True)
    except Exception as e:
        print(f"🚨 Error fetching or scanning DexScreener data: {e}", flush=True)

if __name__ == "__main__":
    startup_msg = "✅ Bot started and ready to snipe\nMonitoring Solana tokens every 5 minutes with LP lock and min $10k liquidity"
    send_telegram_alert(startup_msg)
    while True:
        fetch_and_filter_tokens()
        print("⏳ Finished scan, sleeping 5m", flush=True)
        time.sleep(300)
