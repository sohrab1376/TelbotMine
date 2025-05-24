import json
import asyncio
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from analyzer import analyze_last_candle

TOKEN = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
CHAT_ID_FILE = "chat_id.txt"
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            print("Error in signal loop:", e)
        await asyncio.sleep(300)

async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("viewconfig", view_config))
    application.add_handler(CommandHandler("setconfig", set_config))

    # Start polling and background task
    async with application:
        await application.start()
        asyncio.create_task(signal_check_loop(application))
        await application.updater.start_polling()
        await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())