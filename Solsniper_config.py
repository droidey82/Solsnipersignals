import os

# Telegram bot and chat configurations
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# SolanaStreaming API Key
SOLANASTREAMING_API_KEY = os.getenv("SOLANASTREAMING_API_KEY")

# Mint address filter for tokens (leave empty for all tokens)
FILTER_MINT_ADDRESSES = []  # Add any baseTokenMint values as necessary