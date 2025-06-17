import os
import time
from datetime import datetime
import telegram
import requests
from bs4 import BeautifulSoup

print("[BOOT] Starting SolSniper worker (web-scrape mode)...", flush=True)

# Load ENV vars only
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

bot = telegram.Bot(token=TELEGRAM_TOKEN)
bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🟢 SolSniper web scraper started at " + datetime.utcnow().strftime('%H:%M:%S UTC'))

URL = "https://dexscreener.com/solana"

def fetch_tokens():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(URL, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        rows = soup.select("a[class*='trading-row']")[:10]  # get top 10
        tokens = []

        for row in rows:
            name = row.select_one("div span.font-bold").text.strip()
            pair_url = "https://dexscreener.com" + row["href"]
            volume_str = row.find_all("div")[-1].text.strip().replace("$", "").replace(",", "")
            volume = float(volume_str) if volume_str.replace(".", "").isdigit() else 0

            tokens.append({
                "name": name,
                "url": pair_url,
                "volume": volume
            })

        return tokens
    except Exception as e:
        print("[ERROR] Scraping failed:", str(e), flush=True)
        return []

def main_loop():
    while True:
        print(f"\n[INFO] Scraping tokens at {datetime.utcnow().strftime('%H:%M:%S UTC')}", flush=True)
        tokens = fetch_tokens()
        print(f"[INFO] Found {len(tokens)} tokens", flush=True)

        count = 0
        for t in tokens:
            if t["volume"] >= 10000:
                msg = f"🚀 *{t['name']}* detected!\n📈 Volume: ${t['volume']:,.0f}\n🔗 {t['url']}"
                try:
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)
                    print(f"[✅] Alert sent for {t['name']}", flush=True)
                    count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to send alert for {t['name']}: {e}", flush=True)
            else:
                print(f"[❌] {t['name']} skipped due to low volume (${t['volume']:,.0f})", flush=True)

        if count == 0:
            print("[INFO] No valid tokens this round.", flush=True)

        time.sleep(60)

if __name__ == "__main__":
    main_loop()