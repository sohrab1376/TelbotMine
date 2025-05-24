import json
import logging
import asyncio
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from analyzer import analyze_last_candle
from fastapi import FastAPI
from threading import Thread

TOKEN = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
WEBHOOK_PATH = "/webhook/telegram"
WEBHOOK_URL = "https://your-render-url.onrender.com" + WEBHOOK_PATH
PORT = 8080
CHAT_ID_FILE = "chat_id.txt"

# Load config
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ ربات فعال شد و هر ۵ دقیقه آخرین سیگنال را بررسی می‌کند.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    msg = f"مقادیر فعلی:
a = {config['a']}
b = {config['b']}
combos = {config['combos']}"
    await update.message.reply_text(msg)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    try:
        a = float(args[0])
        b = float(args[1])
        combos = [tuple(map(int, c.split(","))) for c in args[2:]]
        config = {"a": a, "b": b, "combos": combos}
        save_config(config)
        await update.message.reply_text("✅ تنظیمات جدید ثبت شد.")
    except:
        await update.message.reply_text("❌ فرمت دستور اشتباه است. نمونه:
/setconfig 1 1 3,8 3,10 3,11")

# FastAPI app for /wake
app = FastAPI()

@app.post("/wake")
async def wake():
    return {"status": "alive"}

# اجرای حلقه بررسی سیگنال
def start_bot():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("viewconfig", view_config))
    application.add_handler(CommandHandler("setconfig", set_config))

    async def check_loop():
        await application.bot.set_webhook(url=WEBHOOK_URL)
        while True:
            try:
                config = load_config()
                result = analyze_last_candle(config["a"], config["b"], config["combos"])
                if result:
                    with open(CHAT_ID_FILE, "r") as f:
                        chat_id = int(f.read().strip())
                    text = (
                        f"📈 Signal: {result['direction'].upper()}
"
                        f"Entry: {result['entry']:.2f}
"
                        f"TP: {result['tp']:.2f}
"
                        f"SL: {result['sl']:.2f}
"
                        f"Leverage: {result['leverage']}x"
                    )
                    await application.bot.send_message(chat_id=chat_id, text=text)
            except Exception as e:
                print("Error during check_loop:", e)
            await asyncio.sleep(300)

    async def main():
        await check_loop()

    Thread(target=lambda: asyncio.run(main())).start()
    application.run_webhook(listen="0.0.0.0", port=PORT, webhook_path=WEBHOOK_PATH)

# Launch
if __name__ == "__main__":
    start_bot()