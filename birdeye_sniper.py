import os, sys, time, json, asyncio
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from oauth2client.service_account import ServiceAccountCredentials
import gspread

load_dotenv()

def send_telegram_alert(msg):
    token = os.getenv("TELEGRAM_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("❌ Missing Telegram env vars")
        return
    bot = Bot(token=token)
    resp = bot.send_message(chat_id=chat, text=msg)
    print("📤 Telegram alert sent:", resp)

def log_to_google_sheets(row):
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "/etc/secrets/GOOGLE_CREDS_JSON",
            ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        )
        sheet = gspread.authorize(creds).open("Sol Sniper Logs").sheet1
        sheet.append_row(row)
    except Exception as e:
        print("❌ Sheets logging error:", e)

def fetch_token_list():
    url = "https://api.birdeye.so/defi/tokenlist"
    headers = {"Accept": "application/json"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"🛠 Birdeye tokenlist status: {resp.status_code}")
    return resp

def scan_tokens():
    print(f"\n🕵️‍♂️ {datetime.utcnow()} scanning...")

    # Test Telegram
    send_telegram_alert("✅ Birdeye monitoring started!")

    for attempt in range(3):
        resp = fetch_token_list()
        if resp.status_code == 200:
            break
        print("⚠️ Retry", attempt+1, "waiting...")
        time.sleep(10)
    else:
        print("❌ Birdeye failed after retries")
        return

    data = resp.json().get("tokens", [])
    filtered = []
    for t in data:
        try:
            chain = t.get("chain")
            lp = float(t.get("liquidity", {}).get("usd", 0))
            vol = float(t.get("volume_24h", 0))
            hb = float(t.get("holders_share_top", 100))
            locked = t.get("liquidity", {}).get("locked", False)
            burned = t.get("liquidity", {}).get("burned", False)
            if chain == "solana" and lp >= 10000 and vol >= 10000 and hb <= 5 and (locked or burned):
                msg = (
                    f"🚀 {t['name']} ({t['symbol']})\n"
                    f"Liquidity: ${lp:,.0f} | Volume(24h): ${vol:,.0f}\n"
                    f"Top‑holders share: {hb:.1f}%\n"
                    f"Locked: {locked}, Burned: {burned}"
                )
                send_telegram_alert(msg)
                log_to_google_sheets([
                    datetime.utcnow().isoformat(), t['name'], t['symbol'],
                    lp, vol, hb, locked, burned
                ])
                filtered.append(msg)
        except Exception as e:
            print("⚠️ Token parsing error:", e)
    print("✅ Scan done:", len(filtered), "tokens matched.")

if __name__ == "__main__":
    scan_tokens()