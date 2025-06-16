from flask import Flask import threading import asyncio import os import json import websockets from telegram import Bot

=== Environment Variables ===

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SOLANASTREAMING_API_KEY]): raise EnvironmentError("Missing required environment variables")

bot = Bot(token=TELEGRAM_TOKEN)

SUBSCRIBE_MESSAGE = json.dumps({ "id": 1, "method": "swapSubscribe", "params": { "include": { "baseTokenMint": [] } } })

=== Flask Web Server (for BetterStack ping) ===

app = Flask(name)

@app.route('/') def home(): return "Sol Sniper is running!"

=== Telegram Alert ===

async def send_alert(message): try: await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message) except Exception as e: print("Failed to send Telegram alert:", e)

=== WebSocket Stream ===

async def handle_stream(): url = "wss://api.solanastreaming.com/" headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

while True:
    try:
        async with websockets.connect(url, extra_headers=headers) as ws:
            await ws.send(SUBSCRIBE_MESSAGE)
            print("Subscribed to SolanaStreaming")

            while True:
                response = await ws.recv()
                data = json.loads(response)
                print("Received:", data)

                if data.get("method") == "swap":
                    swap = data.get("params", {}).get("data", {})
                    msg = f"Swap Detected:\n{swap.get('baseTokenSymbol')} ➔ {swap.get('quoteTokenSymbol')}\nAmount Out: {swap.get('amountOut')}"
                    await send_alert(msg)

    except Exception as e:
        print("Error in stream loop:", e)
        await asyncio.sleep(5)

=== Startup Threads ===

def start_web(): app.run(host="0.0.0.0", port=10000)

def start_worker(): loop = asyncio.new_event_loop() asyncio.set_event_loop(loop) loop.run_until_complete(handle_stream())

if name == 'main': threading.Thread(target=start_web).start() start_worker()

