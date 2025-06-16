import os
import json
import asyncio
import websockets
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

if TELEGRAM_TOKEN is None:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")
if TELEGRAM_CHAT_ID is None:
    raise ValueError("TELEGRAM_CHAT_ID environment variable not set")
if API_KEY is None:
    raise ValueError("SOLANASTREAMING_API_KEY environment variable not set")

bot = Bot(token=TELEGRAM_TOKEN)

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
        print("❌ Telegram error:", e)

async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {"X-API-KEY": API_KEY}

    async with websockets.connect(url, extra_headers=headers) as ws:
        await ws.send(SUBSCRIBE_MESSAGE)
        print("✅ Subscribed to SolanaStreaming WebSocket")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)
                print("🔁 Data received:", data)

                # Filter: only notify on actual swap events
                if data.get("method") == "swap":
                    token_info = data.get("params", {}).get("data", {})
                    base = token_info.get("baseTokenSymbol", "Unknown")
                    quote = token_info.get("quoteTokenSymbol", "Unknown")
                    amount = token_info.get("amountOut", "0")

                    msg = f"🚨 Swap Detected!\n{base} → {quote}\nAmount Out: {amount}"
                    await send_alert(msg)

            except Exception as e:
                print("⚠️ Error during WebSocket stream:", e)
                await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_stream())