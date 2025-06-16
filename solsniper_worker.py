import asyncio
import json
import os
import websockets
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WS_URL = "wss://ws.solanastreaming.com"

bot = Bot(token=TELEGRAM_TOKEN)

def passes_filters(token):
    try:
        liquidity = float(token.get("liquidity_usd", 0))
        volume = float(token.get("volume_usd", 0))
        lp_locked = token.get("lp_locked", False)
        lp_burned = token.get("lp_burned", False)

        holders = token.get("top_holders", [])
        holders_ok = all(float(h.get("share", 0)) <= 5.0 for h in holders) if holders else True

        return (
            liquidity >= 10000 and
            volume >= 10000 and
            (lp_locked or lp_burned) and
            holders_ok
        )
    except Exception as e:
        print("Filter error:", e)
        return False

async def handle_message(data):
    token = data.get("data", {})
    if not token or not passes_filters(token):
        return

    msg = (
        f"🔥 New Solana Token Detected!\n"
        f"Name: {token.get('name')}\n"
        f"Symbol: {token.get('symbol')}\n"
        f"Liquidity: ${token.get('liquidity_usd', 0):,.0f}\n"
        f"Volume (24h): ${token.get('volume_usd', 0):,.0f}\n"
        f"LP Locked: {token.get('lp_locked')}\n"
        f"LP Burned: {token.get('lp_burned')}\n"
        f"Timestamp: {datetime.utcnow().isoformat()} UTC"
    )
    print("✅ Sending Telegram alert:\n", msg)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

async def listen():
    async with websockets.connect(WS_URL) as ws:
        print("📡 Connected to SolanaStreaming WebSocket")
        await ws.send(json.dumps({
            "type": "subscribe",
            "channel": "recent_tokens",
            "chain_id": "solana"
        }))
        while True:
            try:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("type") == "token":
                    await handle_message(data)
            except Exception as e:
                print("⚠️ WebSocket error:", e)
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen())