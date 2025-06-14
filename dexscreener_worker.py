import os
import requests
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === Telegram Setup ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

# === Google Sheets Setup ===
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(GOOGLE_CREDS_JSON), scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open("SolSniperSignals").sheet1

def log_to_google_sheets(token_data):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        now,
        token_data['name'],
        token_data['symbol'],
        token_data['liquidity'],
        token_data['volume'],
        token_data['dex'],
        token_data['url']
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")

# === DexScreener + Filters ===
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")


def check_dexscreener():
    try:
        res = requests.get(
            "https://api.dexscreener.com/latest/dex/pairs/solana"
        )
        tokens = res.json().get("pairs", [])
    except Exception as e:
        print(f"DexScreener fetch error: {e}")
        return

    print(f"[DEBUG] Scanning {len(tokens)} tokens from DexScreener...")

    for token in tokens:
        try:
            name = token.get("baseToken", {}).get("name", "N/A")
            symbol = token.get("baseToken", {}).get("symbol", "N/A")
            liquidity = float(token.get("liquidity", {}).get("usd", 0))
            volume = float(token.get("volume", {}).get("h5", 0))
            dex = token.get("dexId", "N/A")
            url = f"https://dexscreener.com/solana/{token.get('pairAddress')}"

            # Filters
            if liquidity < 10000:
                continue
            if volume < 2000:
                continue

            # LP locked?
            token_address = token.get("baseToken", {}).get("address")
            birdeye_url = f"https://public-api.birdeye.so/public/token/{token_address}/liquidity-pools"
            headers = {"X-API-KEY": BIRDEYE_API_KEY}
            lp_data = requests.get(birdeye_url, headers=headers).json()
            lp_locked = any("lock" in lp.get("name", "").lower() for lp in lp_data.get("data", []))
            if not lp_locked:
                continue

            print(f"[ALERT] Passed: {name} | Vol: ${volume:.0f} | Liq: ${liquidity:.0f}")

            message = (
                f"<b>🚀 New Token Detected</b>\n"
                f"<b>Name:</b> {name}\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"<b>5m Volume:</b> ${volume:,.0f}\n"
                f"<b>Dex:</b> {dex}\n"
                f"<b>Pair:</b> <a href='{url}'>View</a>"
            )

            send_telegram_alert(message)
            log_to_google_sheets({
                "name": name,
                "symbol": symbol,
                "liquidity": liquidity,
                "volume": volume,
                "dex": dex,
                "url": url
            })

        except Exception as e:
            print(f"Token check error: {e}")

# === Start Bot ===
startup_msg = (
    "<b>✅ Bot started and ready to snipe</b>\n"
    "<i>Monitoring Solana tokens every 5 minutes with LP lock, volume spike and min $10k liquidity</i>"
)
send_telegram_alert(startup_msg)

if __name__ == "__main__":
    while True:
        check_dexscreener()
        time.sleep(300)
