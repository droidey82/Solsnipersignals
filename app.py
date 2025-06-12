@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    if not data:
        return {"error": "No JSON received"}, 400

    token_name = data.get("token", "Unknown Token")
    price = data.get("price", "N/A")
    volume = data.get("volume", "N/A")

    telegram_message = f"🚀 *New Alert:*\nToken: {token_name}\nPrice: {price}\nVolume: {volume}"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_message,
        "parse_mode": "Markdown"
    }

    response = requests.post(TELEGRAM_API_URL, json=payload)

    if response.status_code == 200:
        return {"status": "sent"}, 200
    else:
        # Print Telegram response to debug the issue
        print("Telegram response:", response.text)
        return {
            "error": "Failed to send Telegram message",
            "telegram_response": response.text  # <-- View this in Render logs
        }, 500
