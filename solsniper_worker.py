import os
import json
import time
import requests
from telegram import Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === Load secrets from /etc/secrets ===
TELEGRAM_TOKEN = open("/etc/secrets/TELEGRAM_TOKEN").read().strip()
TELEGRAM_CHAT_ID = open("/etc/secrets/TELEGRAM_CHAT_ID").read().strip()
GOOGLE_CREDS = open("/etc/secrets/GOOGLE_CREDS").read().strip()

# === Setup Telegram bot ===
bot = Bot(token=TELEGRAM_TOKEN)

# === Setup Google Sheets logging ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# === Alert history to avoid duplicates ===
sent_tokens = set()

# === Filters ===
MIN_VOLUME = 10000
MIN_LIQUIDITY = 10000
MIN_MARKET_CAP = 100000
MAX_HOLDER_PERCENT = 5
REQUIRE_BURNED_LP = True

# === Fetch token data from DexScreener ===
def fetch_trending_solana():
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("pairs", [])
        else:
            print(f"API error: {response.status_code}")
            return []
    except Exception as e:
        print("Fetch error:", e)
        return []

# === Send alert to Telegram ===
def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("Telegram error:", e)

# === Log alert to Google Sheet ===
def log_to_sheet(data):
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("baseToken", {}).get("name", "N/A"),
            data.get("priceUsd", 0),
            data.get("volume", {}).get("h24", 0),
            data.get("liquidity", {}).get("usd", 0),
            data.get("fdv", 0),
            data.get("holders", 0),
            data.get("liquidity", {}).get("isBurned", False)
        ])
    except Exception as e:
        print("Sheet error:", e)

# === Main loop ===
def main():
    print("🔄 SolSniper Worker Running")
    while True:
        try:
            tokens = fetch_trending_solana()
            for token in tokens:
                base = token.get("baseToken", {}).get("symbol", "")
                volume = token.get("volume", {}).get("h24", 0)
                liquidity = token.get("liquidity", {}).get("usd", 0)
                market_cap = token.get("fdv", 0)
                holders = token.get("holders", 0)
                top_holder = token.get("topHolderPercent", 100)
                burned_lp = token.get("liquidity", {}).get("isBurned", False)

                if base in sent_tokens:
                    continue

                if volume >= MIN_VOLUME and liquidity >= MIN_LIQUIDITY and market_cap >= MIN_MARKET_CAP:
                    if holders > 0 and top_holder <= MAX_HOLDER_PERCENT:
                        if not REQUIRE_BURNED_LP or burned_lp:
                            message = f"🚀 Token Alert: {base}\n💰 Price: ${token.get('priceUsd', 0):.6f}\n📊 Volume: ${volume:,.0f}\n💧 Liquidity: ${liquidity:,.0f}\n🏷️ FDV: ${market_cap:,.0f}\n👥 Holders: {holders}\n🔥 LP Burned: {burned_lp}"
                            send_alert(message)
                            log_to_sheet(token)
                            sent_tokens.add(base)

            time.sleep(60)
        except Exception as e:
            print("Loop error:", e)
            time.sleep(30)

if __name__ == '__main__':
    send_alert("🟢 SolSniper Bot is live and monitoring Solana tokens.")
    main()
