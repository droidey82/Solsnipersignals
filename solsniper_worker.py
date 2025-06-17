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
GOOGLE_CREDS_PATH = "/etc/secrets/GOOGLE_CREDS"  # Secret mount

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
    last_keepalive = datetime.utcnow()

    async with websockets.connect(url, extra_headers=headers) as ws:
        await send_alert("🟢 SolSniper Bot has started and is now monitoring the Solana memecoin market.")
        await ws.send(SUBSCRIBE_MESSAGE)
        print(f"[{datetime.utcnow()}] ✅ Subscribed to SolanaStreaming WebSocket")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)
                now = datetime.utcnow()

                if (now - last_keepalive).seconds > 60:
                    print(f"[{now}] 🔄 Waiting for matching swaps...")
                    last_keepalive = now

                if data.get("method") != "swap":
                    continue

                print(f"[{now}] 🔍 Swap event received")

                info = data.get("params", {}).get("data", {})
                token = info.get("baseTokenSymbol")
                price = info.get("priceUsd", 0)
                volume = info.get("volumeUsd", 0)
                liquidity = info.get("liquidityUsd", 0)
                holders = info.get("holders", 0)
                market_cap = info.get("fdvUsd", 0)
                top_holder = info.get("topHolderPercent", 100)

                print(f"    → Token: {token}, Volume: {volume}, Liquidity: {liquidity}, FDV: {market_cap}")

                if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY or market_cap < MIN_MARKET_CAP:
                    print("    ✖ Swap filtered: low volume/liquidity/market cap")
                    continue
                if holders == 0 or top_holder > MAX_HOLDER_PERCENT:
                    print("    ✖ Swap filtered: holder concentration or no holders")
                    continue

                message = (
                    f"🚀 New Token Detected\n"
                    f"Name: {token}\nPrice: ${price:.6f}\n"
                    f"Volume: ${volume:,.0f}\nLiquidity: ${liquidity:,.0f}\n"
                    f"FDV: ${market_cap:,.0f}\nHolders: {holders}"
                )

                print("    ✅ Match found, sending alert + logging")
                await send_alert(message)
                await log_to_sheet(token, price, volume, liquidity, holders, market_cap)

            except Exception as e:
                print(f"[{datetime.utcnow()}] ❌ Stream error:", e)
                await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_stream())
