const express = require("express");
const bodyParser = require("body-parser");

const app = express();
app.use(bodyParser.json());

app.post("/webhook", async (req, res) => {
  console.log("Received alert:", req.body);

  const { token, symbol, price, volume } = req.body;
  if (token && symbol) {
    const message = `💥 New Memecoin Signal\nToken: ${symbol}\nPrice: $${price}\nVolume: $${volume}`;
    await fetch(`https://api.telegram.org/bot${process.env.BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: process.env.CHAT_ID,
        text: message,
      }),
    });
  }

  res.sendStatus(200);
});

app.get("/", (req, res) => res.send("Bot is live!"));
app.listen(process.env.PORT || 3000, () => {
  console.log("Server running...");
});
