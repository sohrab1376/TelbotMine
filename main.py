import json
import asyncio
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from analyzer import analyze_last_candle

print("✅ main.py started")

# Start dummy HTTP server for Render
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"I'm alive!")

def run_dummy_server():
    print("🌐 Starting dummy HTTP server on port 10000")
    server = HTTPServer(("0.0.0.0", 10000), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# Telegram bot config
TOKEN = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
CHAT_ID_FILE = "chat_id.txt"
CONFIG_FILE = "config.json"

print("📂 Working directory:", os.getcwd())
print("📄 Files in directory:", os.listdir())

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ /start command received")
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ Bot is active. It will check for new signals every 5 minutes.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    msg = f"""Current Config:
a = {config['a']}
b = {config['b']}
combos = {config['combos']}"""
    await update.message.reply_text(msg)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    try:
        a = float(args[0])
        b = float(args[1])
        combos = [tuple(map(int, c.split(","))) for c in args[2:]]
        config = {"a": a, "b": b, "combos": combos}
        save_config(config)
        await update.message.reply_text("✅ New settings saved.")
    except:
        await update.message.reply_text("❌ Invalid format. Example:\n/setconfig 1 1 3,8 3,10 3,11")

async def signal_check_loop(app):
    print("⏱️ Signal loop started")
    while True:
        try:
            config = load_config()
            result = analyze_last_candle(config["a"], config["b"], config["combos"])
            if result:
                with open(CHAT_ID_FILE, "r") as f:
                    chat_id = int(f.read().strip())
                text = (
                    f"📈 Signal: {result['direction'].upper()}\n"
                    f"Entry: {result['entry']:.2f}\n"
                    f"TP: {result['tp']:.2f}\n"
                    f"SL: {result['sl']:.2f}\n"
                    f"Leverage: {result['leverage']}x"
                )
                await app.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print("❌ Error in signal loop:", e)
        await asyncio.sleep(300)

async def main():
    print("🚀 main() started")
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("viewconfig", view_config))
    application.add_handler(CommandHandler("setconfig", set_config))
    print("✅ Handlers added")

    async with application:
        await application.start()
        print("🤖 Bot started")
        asyncio.create_task(signal_check_loop(application))
        await application.updater.start_polling()
        print("📡 Polling started")
        await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())