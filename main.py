import os
import json
import asyncio
import pandas as pd
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
)

from analyzer import analyze_last_candle

# ﺗﻮﻛﻦ ﻭ WEBHOOK ﺧﻮﺩﺕ
TOKEN = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = "https://telegram-tradebot.onrender.com" + WEBHOOK_PATH

# فایل‌های ذخیره‌سازی
CHAT_ID_FILE = "chat_id.txt"
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

# ﺳﺎﺧﺖ هندلر‌ها
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ذخیره chat_id
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ Bot is live via Webhook.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    text = f"Current Config:\na = {cfg['a']}\nb = {cfg['b']}\ncombos = {cfg['combos']}"
    await update.message.reply_text(text)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        a = float(args[0]); b = float(args[1])
        combos = [tuple(map(int, x.split(","))) for x in args[2:]]
        cfg = {"a": a, "b": b, "combos": combos}
        save_config(cfg)
        await update.message.reply_text("✅ Config updated.")
    except:
        await update.message.reply_text("❌ Invalid format. Use:\n/setconfig 1 1 3,8 3,10 3,11")

# حلقه‌ی پس‌زمینه برای سیگنال
async def signal_loop(app: Application):
    while True:
        try:
            cfg = load_config()
            sig = analyze_last_candle(cfg["a"], cfg["b"], cfg["combos"])
            if sig:
                with open(CHAT_ID_FILE, "r") as f:
                    chat_id = int(f.read().strip())
                msg = (
                    f"📈 Signal: {sig['direction'].upper()}\n"
                    f"Entry: {sig['entry']:.2f}\n"
                    f"TP: {sig['tp']:.2f}\n"
                    f"SL: {sig['sl']:.2f}\n"
                    f"Leverage: {sig['leverage']}x"
                )
                await app.bot.send_message(chat_id=chat_id, text=msg)
        except Exception as e:
            print("⚠️ signal_loop error:", e)
        await asyncio.sleep(300)

def main():
    # ۱) ساخت شئ Application
    app = ApplicationBuilder().token(TOKEN).build()
    # ۲) افزودن handlerها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("viewconfig", view_config))
    app.add_handler(CommandHandler("setconfig", set_config))
    # ۳) ست کردن Webhook در تلگرام
    app.bot.set_webhook(WEBHOOK_URL)
    # ۴) استارت حلقه‌ی سیگنال (پیش از run_webhook)
    asyncio.create_task(signal_loop(app))
    # ۵) اجرای وبهوک (بلوک‌کننده)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
