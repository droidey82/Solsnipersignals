import os
import json
import asyncio
import websockets
from telegram import Bot

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

# Validate
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not SOLANASTREAMING_API_KEY:
    raise EnvironmentError("One or more required environment variables are missing.")

# Initialize bot
bot = Bot(token=TELEGRAM_TOKEN)

# Example subscribe message — you can update filters later
SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []  # Track all tokens or add specific token mints
        }
    }
})

async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("❌ Failed to send Telegram message:", repr(e))

async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {
        "X-API-KEY": SOLANASTREAMING_API_KEY
    }

    async with websockets.connect(url, extra_headers=headers) as ws:
        await ws.send(SUBSCRIBE_MESSAGE)
        print("✅ Subscribed to SolanaStreaming WebSocket")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)
                print("🔄 Received:", data)

                # Example filter for swap notifications
                if data.get("method") == "swap":
                    token_info = data.get("params", {}).get("data", {})
                    base = token_info.get("baseTokenSymbol", "Unknown")
                    quote = token_info.get("quoteTokenSymbol", "Unknown")
                    amount = token_info.get("amountOut", "N/A")

                    message = f"🚨 Swap Detected:\n{base} → {quote}\nAmount Out: {amount}"
                    await send_alert(message)

            except Exception as e:
                print("⚠️ Error in stream loop:", repr(e))
                await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(handle_stream())