import os
import requests
import time
import datetime
import json
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import gspread

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

def send_telegram_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        print("📨 Telegram response:", response.status_code, "-", response.text[:500])
    except Exception as e:
        print("❌ Telegram send failed:", e)

def log_to_google_sheets(data_row):
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        sh = gc.open("Sol Sniper Logs").sheet1
        sh.append_row(data_row)
        print("🟢 Logged to Google Sheets.")
    except Exception as e:
        print("❌ Google Sheets log failed:", e)

def check_dexscreener():
    print(f"\n🧑‍🚀 {datetime.datetime.utcnow()} - Scanning Solana tokens...", flush=True)
    try:
        url = "https://api.dexscreener.io/latest/dex/pairs/solana"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid DexScreener API response: {response.status_code} - {response.text[:100]}")
        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            print("🔴 No valid pairs data found.")
            return

        filtered = []
        for pair in pairs:
            try:
                base_token = pair["baseToken"]
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                volume_5m = float(pair.get("volume", {}).get("usd", {}).get("m5", 0))
                volume_15m = float(pair.get("volume", {}).get("usd", {}).get("m15", 0))
                top_holders = pair.get("info", {}).get("fullyDilutedValuation", 0)
                holders = pair.get("holders", [])
                top_holder_pct = max([h.get("share", 0) for h in holders]) if holders else 100

                # Safety filters
                if not pair.get("liquidity", {}).get("lock"):
                    continue
                if liquidity < 10000:
                    continue
                if volume_5m < volume_15m * 1.2:  # 20% volume spike
                    continue
                if top_holder_pct > 5:
                    continue

                msg = (
                    f"<b>🔥 Sol Token Alert</b>\n"
                    f"{base_token['name']} ({base_token['symbol']})\n"
                    f"💧 Liquidity: ${liquidity:,.0f}\n"
                    f"📈 Volume (5m): ${volume_5m:,.0f}\n"
                    f"🧠 Top Holder: {top_holder_pct:.1f}%\n"
                    f"<a href=\"{pair['url']}\">View Chart</a>"
                )

                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.datetime.utcnow().isoformat(),
                    base_token["name"],
                    base_token["symbol"],
                    liquidity,
                    volume_5m,
                    top_holder_pct,
                    pair["url"]
                ])
                filtered.append(msg)
            except Exception as e:
                print(f"❌ Error parsing pair: {e}")

        print(f"✅ Scan complete. {len(filtered)} tokens passed filters.", flush=True)
    except Exception as e:
        print(f"🚨 Error fetching or scanning DexScreener data: {e}")

if __name__ == "__main__":
    startup_msg = (
        "<b>✅ Bot started and ready to snipe</b>\n"
        "<i>Monitoring Solana tokens every 5 minutes with LP lock, "
        "top holders ≤5% and min $10k liquidity</i>"
    )
    send_telegram_alert(startup_msg)

    while True:
        check_dexscreener()
        print("⏳ Finished scan, sleeping 5m")
        time.sleep(300)