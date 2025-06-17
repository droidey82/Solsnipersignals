import os
import json
import asyncio
import websockets
from telegram import Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import traceback

# Load secrets and environment vars
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")
GOOGLE_CREDS_PATH = "/etc/secrets/GOOGLE_CREDS"

# Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

# Google Sheets setup
with open(GOOGLE_CREDS_PATH) as f:
    creds_dict = json.load(f)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Sol Sniper Logs").sheet1

# Filters
MIN_VOLUME = 10000
MIN_LIQUIDITY = 10000
MAX_HOLDER_PERCENT = 5
MIN_MARKET_CAP = 100000

SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []
        }
    }
})

sent_startup_message = False

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
    global sent_startup_message
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}
    url = "wss://api.solanastreaming.com"

    while True:
        try:
            print("🔌 Connecting to WebSocket...")
            async with websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=60,
                ping_timeout=20,
                close_timeout=5
            ) as ws:
                print("✅ Connected to SolanaStreaming")
                if not sent_startup_message:
                    await send_alert("🟢 SolSniper Bot is live and monitoring swaps.")
                    sent_startup_message = True

                await ws.send(SUBSCRIBE_MESSAGE)
                print("📡 Subscribed to token swaps")

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
                        top_holder = info.get("topHolderPercent", 100)

                        if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY or market_cap < MIN_MARKET_CAP:
                            continue
                        if holders == 0 or top_holder > MAX_HOLDER_PERCENT:
                            continue

                        msg = (
                            f"🚀 New Token Detected\n"
                            f"Name: {token}\n"
                            f"Price: ${price:.6f}\n"
                            f"Volume: ${volume:,.0f}\n"
                            f"Liquidity: ${liquidity:,.0f}\n"
                            f"FDV: ${market_cap:,.0f}\n"
                            f"Holders: {holders}"
                        )

                        await send_alert(msg)
                        await log_to_sheet(token, price, volume, liquidity, holders, market_cap)

                    except Exception as e:
                        print("⚠️ Stream error:", e)
                        traceback.print_exc()
                        break  # force reconnect

        except Exception as e:
            print("🔁 Reconnect after WebSocket error:", e)
            traceback.print_exc()
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(handle_stream())