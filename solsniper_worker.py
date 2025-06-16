import os
import json
import asyncio
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if TELEGRAM_TOKEN is None:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

bot = Bot(token=TELEGRAM_TOKEN)

SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            # Filter by known token mints or leave empty for all
            # Example token: 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr
            "baseTokenMint": []
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
    headers = {"X-API-KEY": API_KEY}

    async with websockets.connect(url, extra_headers=headers) as ws:
        await ws.send(SUBSCRIBE_MESSAGE)
        print("Subscribed to SolanaStreaming WebSocket")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)

                # Basic logging
                print("Received:", data)

                # === Add logic to filter based on LP, volume, holders, etc ===
                # Placeholder: send all swaps to Telegram
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
