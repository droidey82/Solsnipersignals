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
GOOGLE_CREDS_PATH = "/etc/secrets/GOOGLE_CREDS"

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Setup Google Sheets logging
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
with open(GOOGLE_CREDS_PATH) as f:
    creds_dict = json.load(f)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# Filter parameters
MIN_VOLUME = 10000  # $10k
MIN_LIQUIDITY = 10000  # $10k
MAX_HOLDER_PERCENT = 5
MIN_MARKET_CAP = 100000  # $100k

# Subscription message template
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenSymbol": []
        }
    }
})

async def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
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

    while True:
        try:
            async with websockets.connect(url, extra_headers=headers, ping_interval=None) as ws:
                print("Connected to WebSocket")
                await ws.send(SUBSCRIBE_MESSAGE)
                print("Subscribed to SolanaStreaming WebSocket")

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
                    top_holder = info.get("topHolderPercent", 100)

                    if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY or market_cap < MIN_MARKET_CAP:
                        continue
                    if holders == 0 or top_holder > MAX_HOLDER_PERCENT:
                        continue

                    message = f"🚀 New Token Detected\nName: {token}\nPrice: ${price:.6f}\nVolume: ${volume:,.0f}\nLiquidity: ${liquidity:,.0f}\nFDV: ${market_cap:,.0f}\nHolders: {holders}"
                    await send_alert(message)
                    await log_to_sheet(token, price, volume, liquidity, holders, market_cap)

        except websockets.exceptions.ConnectionClosedError as e:
            print("Connection closed with error:", e)
        except Exception as e:
            print("Unexpected error:", e)

        print("Reconnecting in 5 seconds...")
        await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(handle_stream())
