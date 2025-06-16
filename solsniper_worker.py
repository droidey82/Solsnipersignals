import os
import json
import asyncio
import websockets
from telegram import Bot

# === Environment Variables ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANA_API_KEY = os.getenv("SOLANA_API_KEY")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not SOLANA_API_KEY:
    raise EnvironmentError("One or more required environment variables are missing.")

bot = Bot(token=TELEGRAM_TOKEN)

SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []  # Empty to listen to all tokens
        }
    }
})

async def send_alert(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print("❌ Failed to send Telegram alert:", e)

async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {"X-API-KEY": SOLANA_API_KEY}

    try:
        async with websockets.connect(
            url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=20
        ) as ws:
            await ws.send(SUBSCRIBE_MESSAGE)
            print("✅ Subscribed to SolanaStreaming WebSocket")
            await send_alert("🟢 Solana Sniper bot connected and listening for swaps...")

            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    print("Received:", data)

                    # === Swap Alert Logic ===
                    if data.get("method") == "swap":
                        swap_data = data.get("params", {}).get("data", {})
                        base = swap_data.get("baseTokenSymbol", "")
                        quote = swap_data.get("quoteTokenSymbol", "")
                        amount = swap_data.get("amountOut", "N/A")
                        message = f"🚨 Swap Detected!\n{base} → {quote}\nAmount Out: {amount}"
                        await send_alert(message)

                except Exception as e:
                    print("⚠️ Error during WebSocket stream:", e)
                    await asyncio.sleep(5)

    except Exception as e:
        print("❌ Failed to connect to WebSocket:", e)
        await send_alert("❌ Failed to connect to SolanaStreaming WebSocket")

if __name__ == '__main__':
    asyncio.run(handle_stream())