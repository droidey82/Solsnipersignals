import os
import json
import asyncio
import websockets
from telegram import Bot
from decimal import Decimal

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not SOLANASTREAMING_API_KEY:
    raise EnvironmentError("Missing one or more environment variables")

bot = Bot(token=TELEGRAM_TOKEN)

SUBSCRIBE_MESSAGE = json.dumps({
    "id": 1,
    "method": "swapSubscribe",
    "params": {
        "include": {
            "baseTokenMint": []  # Subscribe to all tokens
        }
    }
})

async def send_alert(message: str):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"Telegram error: {e}")


def is_valid_token(data):
    """Apply filtering logic to determine if token meets requirements."""
    try:
        info = data["params"]["data"]

        volume = Decimal(info.get("volume24h", 0))
        liquidity = Decimal(info.get("liquidity", 0))
        market_cap = Decimal(info.get("fdv", 0))
        holders = int(info.get("holders", 0))
        lp_burned = info.get("lpLocked", False)
        top_holder_percent = Decimal(info.get("topHolderPercent", 100))

        return (
            volume >= 10000 and
            liquidity >= 10000 and
            market_cap >= 100000 and
            lp_burned and
            top_holder_percent <= 5
        )
    except Exception as e:
        print(f"Filter error: {e}")
        return False


async def handle_stream():
    url = "wss://api.solanastreaming.com/"
    headers = {"X-API-KEY": SOLANASTREAMING_API_KEY}

    async with websockets.connect(url, extra_headers=headers) as ws:
        await ws.send(SUBSCRIBE_MESSAGE)
        print("✅ Subscribed to SolanaStreaming")

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)

                if data.get("method") == "swap" and is_valid_token(data):
                    token = data["params"]["data"]
                    base = token.get("baseTokenSymbol")
                    quote = token.get("quoteTokenSymbol")
                    tx = token.get("txHash", "")
                    volume = token.get("volume24h")
                    liquidity = token.get("liquidity")

                    message = (
                        f"🚨 New Trade Alert 🚨\n"
                        f"Token: {base}/{quote}\n"
                        f"24h Volume: ${volume}\n"
                        f"Liquidity: ${liquidity}\n"
                        f"Tx: https://solscan.io/tx/{tx}"
                    )
                    await send_alert(message)

            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(5)


if __name__ == '__main__':
    asyncio.run(handle_stream())
