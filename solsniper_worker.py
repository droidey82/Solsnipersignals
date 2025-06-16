import os
import json
import asyncio
import websockets
from telegram import Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

# Path to Google Sheets credentials (Render secret mount)
GOOGLE_CREDS_PATH = "/etc/secrets/GOOGLE_CREDS"

# Setup Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Setup Google Sheets logging
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
with open(GOOGLE_CREDS_PATH) as f:
    creds_dict = json.load(f)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# Filter parameters
MIN_VOLUME = 10000
MIN_LIQUIDITY = 10000
MAX_HOLDER_PERCENT = 5
MIN_MARKET_CAP = 100000

# WebSocket subscription message
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []
        }
    }
})

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
        print("Sheet logging error:", e)

async def handle_stream():
    url = "wss://api.solanastreaming.com"
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

    try:
        async with websockets.connect(url, extra_headers=headers) as ws:
            print("✅ Connected to SolanaStreaming WebSocket.")
            await ws.send(SUBSCRIBE_MESSAGE)

            # Send startup alert ONCE after successful subscription
            await send_alert("🟢 SolSniper Bot is live and monitoring swaps.")

            while True:
                try:
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
                    top_holder_percent = info.get("topHolderPercent", 100)

                    # Apply filters
                    if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY or market_cap < MIN_MARKET_CAP:
                        continue
                    if holders == 0 or top_holder_percent > MAX_HOLDER_PERCENT:
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

                except Exception as stream_err:
                    print("Stream error:", stream_err)
                    await asyncio.sleep(5)

    except Exception as conn_err:
        print("WebSocket connection error:", conn_err)

if __name__ == '__main__':
    asyncio.run(handle_stream())