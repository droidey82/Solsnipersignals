import os
import json
import asyncio
from telegram import Bot
import websockets

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANA_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

# Validate environment variables
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not SOLANA_API_KEY:
    raise EnvironmentError("One or more required environment variables are missing.")

# Initialize bot
bot = Bot(token=TELEGRAM_TOKEN)

# WebSocket subscription message (edit token list if needed)
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []  # Optional: list token mints or leave empty for all
        }
    }
})

# Send Telegram alert
async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("❌ Telegram error:", e)

# Main stream handler
async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {"X-API-KEY": SOLANA_API_KEY}

    try:
        async with websockets.connect(url, extra_headers=headers) as ws:
            await ws.send(SUBSCRIBE_MESSAGE)
            print("✅ Subscribed to SolanaStreaming WebSocket")

            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    print("📥 Received:", data)

                    if data.get("method") == "swap":
                        token_info = data.get("params", {}).get("data", {})
                        base = token_info.get("baseTokenSymbol", "")
                        quote = token_info.get("quoteTokenSymbol", "")
                        amount = token_info.get("amountOut", 0)

                        message = f"🚨 Swap Detected:\n{base} → {quote}\nAmount Out: {amount}"
                        await send_alert(message)

                except Exception as e:
                    print("⚠️ Error in stream loop:", e)
                    await asyncio.sleep(5)

    except Exception as e:
        print("❌ Connection error:", e)

# Entry point
if __name__ == '__main__':
    asyncio.run(handle_stream())