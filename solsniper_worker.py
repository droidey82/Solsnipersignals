import os
import json
import asyncio
import websockets
from telegram import Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")
GOOGLE_CREDS_PATH = "/etc/secrets/GOOGLE_CREDS"  # ✅ Render secret file path

# Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
with open(GOOGLE_CREDS_PATH, "r") as f:
    creds_dict = json.load(f)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# Filter Parameters
MIN_VOLUME = 10000
MIN_LIQUIDITY = 10000
MAX_HOLDER_PERCENT = 5
MIN_MARKET_CAP = 100000

# WebSocket Subscribe Message
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []
        }
    }
})

# Startup Alert Flag
startup_alert_sent = False

async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("Telegram error:", e)

async def log_to_sheet(token, price, volume, liquidity, holders, market_cap):
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            token,
            price,
            volume,
            liquidity,
            holders,
            market_cap
        ])
    except Exception as e:
        print("Google Sheets logging error:", e)

async def handle_stream():
    global startup_alert_sent
    url = "wss://api.solanastreaming.com"
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

    while True:
        try:
            async with websockets.connect(url, extra_headers=headers) as ws:
                if not startup_alert_sent:
                    await send_alert("🟢 SolSniper Bot is live and monitoring swaps.")
                    startup_alert_sent = True

                await ws.send(SUBSCRIBE_MESSAGE)
                print("✅ Subscribed to SolanaStreaming WebSocket")

                while True:
                    response = await ws.recv()
                    data = json.loads(response)

                    if data.get("method") != "swap":
                        continue

                    info = data.get("params", {}).get("data", {})

                    token = info.get("baseTokenSymbol")
                    price = info.get("priceUsd", 0)
                    volume = info.get("volumeUsd", 0)
                    liquidity = info.get("liquidityUsd", 0)
                    holders = info.get("holders", 0)
                    market_cap = info.get("fdvUsd", 0)

                    if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY or market_cap < MIN_MARKET_CAP:
                        continue
                    if holders == 0 or info.get("topHolderPercent", 100) > MAX_HOLDER_PERCENT:
                        continue

                    message = (
                        f"🚀 New Token Detected\n"
                        f"Name: {token}\n"
                        f"Price: ${price:.6f}\n"
                        f"Volume: ${volume:,.0f}\n"
                        f"Liquidity: ${liquidity:,.0f}\n"
                        f"FDV: ${market_cap:,.0f}\n"
                        f"Holders: {holders}"
                    )

                    await send_alert(message)
                    await log_to_sheet(token, price, volume, liquidity, holders, market_cap)

        except Exception as e:
            print("⚠️ Stream error:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(handle_stream())