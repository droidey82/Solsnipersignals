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
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Setup Google Sheets logging
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# Filter thresholds
MIN_VOLUME = 10000       # $10k
MIN_LIQUIDITY = 10000    # $10k
MAX_HOLDER_PERCENT = 5
MIN_MARKET_CAP = 100000  # $100k

# Subscribe to all swaps with volume > $10k
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "swapVolumeUsd": { "gt": MIN_VOLUME }
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
        print("Google Sheets logging error:", e)

async def handle_stream():
    url = "wss://api.solanastreaming.com"
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

    async with websockets.connect(url, extra_headers=headers) as ws:
        print("✅ Subscribed to SolanaStreaming WebSocket")
        await ws.send(SUBSCRIBE_MESSAGE)

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)

                if data.get("method") != "swap":
                    continue

                info = data.get("params", {}).get("data", {})
                token = info.get("baseTokenSymbol", "Unknown")
                price = info.get("priceUsd", 0)
                volume = info.get("volumeUsd", 0)
                liquidity = info.get("liquidityUsd", 0)
                holders = info.get("holders", 0)
                market_cap = info.get("fdvUsd", 0)
                top_holder = info.get("topHolderPercent", 100)

                # Filtering logic
                if (
                    volume < MIN_VOLUME or
                    liquidity < MIN_LIQUIDITY or
                    market_cap < MIN_MARKET_CAP or
                    holders == 0 or
                    top_holder > MAX_HOLDER_PERCENT
                ):
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
                print("Error during stream:", e)
                await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_stream())