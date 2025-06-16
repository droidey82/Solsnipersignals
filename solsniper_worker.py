import os
import json
import asyncio
import websockets
from telegram import Bot
from solsniper_config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SOLANASTREAMING_API_KEY, FILTER_MINT_ADDRESSES

if TELEGRAM_TOKEN is None or TELEGRAM_CHAT_ID is None:
    raise ValueError("Telegram token and chat ID must be set in environment variables.")

bot = Bot(token=TELEGRAM_TOKEN)

# WebSocket subscribe message (filter by mint addresses if needed)
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": FILTER_MINT_ADDRESSES  # Can add mint addresses here to filter specific tokens
        }
    }
})

async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("Failed to send alert:", e)

async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

    async with websockets.connect(url, extra_headers=headers) as ws:
        await ws.send(SUBSCRIBE_MESSAGE)
        print("Subscribed to SolanaStreaming WebSocket")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)

                # Basic logging
                print("Received:", data)

                # Filter based on swap data and send alert
                if data.get("method") == "swap":
                    token_info = data.get("params", {}).get("data", {})
                    base = token_info.get("baseTokenSymbol", "")
                    quote = token_info.get("quoteTokenSymbol", "")
                    amount = token_info.get("amountOut", 0)

                    message = f"Swap Detected:\n{base} → {quote}\nAmount Out: {amount}"
                    await send_alert(message)

            except Exception as e:
                print("Error during stream:", e)
                await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_stream())