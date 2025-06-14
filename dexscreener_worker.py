import os
import requests
import time
from datetime import datetime, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup (with secret file)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/google_creds.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open("Sol Sniper Logs").sheet1

# Telegram setup
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"


def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print("Telegram response:", response.status_code, response.text)
    except Exception as e:
        print("❌ Error sending Telegram alert:", str(e))


def log_to_sheet(token_name, symbol, liquidity, volume, dex, pair_url):
    try:
        sheet.append_row([
            str(datetime.now(timezone.utc)), token_name, symbol,
            f"${liquidity:,}", f"${volume:,}", dex, pair_url
        ])
        print("✅ Logged to Google Sheet")
    except Exception as e:
        print("❌ Error logging to Google Sheet:", e)


def check_dexscreener():
    print(f"\n🧪 {datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        res = requests.get(DEXSCREENER_URL)
        data = res.json()
        pairs = data.get("pairs", [])

        print(f"🧪 Found {len(pairs)} tokens, applying filters...")

        for pair in pairs:
            try:
                token_name = pair.get("baseToken", {}).get("name", "N/A")
                symbol = pair.get("baseToken", {}).get("symbol", "N/A")
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                dex = pair.get("dexId", "N/A")
                url = pair.get("url", "")
                holders = pair.get("holders", [])
                top_holder = max(holders, key=lambda h: h.get("share", 0), default={}).get("share", 0)
                lp_locked = "UNLOCKED" not in pair.get("liquidity", {}).get("lockStatus", "LOCKED")

                if liquidity >= 10000 and top_holder <= 5 and lp_locked:
                    msg = (
                        f"<b>🚀 Token Alert</b>\n"
                        f"<b>Name:</b> {token_name}\n"
                        f"<b>Symbol:</b> {symbol}\n"
                        f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                        f"<b>Top Holder:</b> {top_holder:.2f}%\n"
                        f"<b>Dex:</b> {dex}\n"
                        f"<b>Pair:</b> <a href='{url}'>View on Dexscreener</a>"
                    )
                    send_telegram_alert(msg)
                    log_to_sheet(token_name, symbol, liquidity, volume, dex, url)

            except Exception as inner:
                print("⚠️ Error with token:", inner)

    except Exception as outer:
        print("❌ Error fetching or scanning DexScreener data:", outer)


# Startup message
startup_msg = (
    "✅ <b>Bot started and ready to snipe</b>\n"
    "<i>Monitoring Solana tokens every 5 minutes with LP lock, top holders ≤ 5% and min $10k liquidity</i>"
)
send_telegram_alert(startup_msg)

# Run loop
if __name__ == "__main__":
    while True:
        check_dexscreener()
        print("✅ Finished scan, sleeping 5m\n")
        time.sleep(300)
