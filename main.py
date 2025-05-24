import json
import os
import asyncio
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
from fastapi import FastAPI, Request

from analyzer import analyze_last_candle

TOKEN = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = "https://telegram-tradebot.onrender.com" + WEBHOOK_PATH
CHAT_ID_FILE = "chat_id.txt"
CONFIG_FILE = "config.json"

# بارگذاری و ذخیره‌سازی تنظیمات
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# هندلرهای تلگرام
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ Bot is live via Webhook.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    text = f"Current Config:\na = {cfg['a']}\nb = {cfg['b']}\ncombos = {cfg['combos']}"
    await update.message.reply_text(text)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    try:
        a = float(args[0])
        b = float(args[1])
        combos = [tuple(map(int, x.split(','))) for x in args[2:]]
        cfg = {"a": a, "b": b, "combos": combos}
        save_config(cfg)
        await update.message.reply_text("✅ Config updated.")
    except:
        # استفاده از escape برای newline به جای نوشتن مستقیم newline در رشته
        await update.message.reply_text("❌ Invalid format. Use:\n/setconfig 1 1 3,8 3,10 3,11")

# حلقه بررسی سیگنال
async def signal_check_loop(app: Application):
    while True:
        try:
            cfg = load_config()
            result = analyze_last_candle(cfg["a"], cfg["b"], cfg["combos"])
            if result:
                with open(CHAT_ID_FILE, "r") as f:
                    chat_id = int(f.read().strip())
                msg = (
                    f"📈 Signal: {result['direction'].upper()}\n"
                    f"Entry: {result['entry']:.2f}\n"
                    f"TP: {result['tp']:.2f}\n"
                    f"SL: {result['sl']:.2f}\n"
                    f"Leverage: {result['leverage']}x"
                )
                await app.bot.send_message(chat_id=chat_id, text=msg)
        except Exception as e:
            print("❌ Signal loop error:", e)
        await asyncio.sleep(300)

# اجرای Webhook
async def main():
    # FastAPI endpoint (بی‌استفاده در این ساختار، فقط برای Render)
    fastapi_app = FastAPI()

    @fastapi_app.post(WEBHOOK_PATH)
    async def webhook_handler(request: Request):
        update = await request.json()
        # اجازه بده ApplicationBuilder هندل کنه
        return {"ok": True}

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("viewconfig", view_config))
    application.add_handler(CommandHandler("setconfig", set_config))

    # ست کردن webhook در تلگرام
    await application.bot.set_webhook(url=WEBHOOK_URL)
    # استارت حلقه سیگنال
    asyncio.create_task(signal_check_loop(application))

    # اجرای FastAPI + Telegram webhook با uvicorn
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())