import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from analyzer import analyze_last_candle

# Configuration
TOKEN = os.environ.get("BOT_TOKEN", "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA")
CONFIG_FILE = "config.json"
CHAT_ID_FILE = "chat_id.txt"
WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = f"https://telegram-tradebot.onrender.com{WEBHOOK_PATH}"

# Load and save config
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(chat_id))
    await update.message.reply_text("✅ Bot is live via Webhook.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    text = f"Current Config:\na = {cfg['a']}\nb = {cfg['b']}\ncombos = {cfg['combos']}"
    await update.message.reply_text(text)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    try:
        a = float(args[0]); b = float(args[1])
        combos = [tuple(map(int, x.split(","))) for x in args[2:]]
        cfg = {"a": a, "b": b, "combos": combos}
        save_config(cfg)
        await update.message.reply_text("✅ Config updated.")
    except Exception:
        await update.message.reply_text("❌ Invalid format. Use:\n/setconfig 1 1 3,8 3,10 3,11")

# Signal job callback
async def signal_callback(context: ContextTypes.DEFAULT_TYPE):
    try:
        cfg = load_config()
        sig = analyze_last_candle(cfg["a"], cfg["b"], cfg["combos"])
        if sig:
            with open(CHAT_ID_FILE, "r") as f:
                chat_id = int(f.read().strip())
            text = (
                f"📈 Signal: {sig['direction'].upper()}\n"
                f"Entry: {sig['entry']:.2f}\n"
                f"TP: {sig['tp']:.2f}\n"
                f"SL: {sig['sl']:.2f}\n"
                f"Leverage: {sig['leverage']}x"
            )
            await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print("⚠️ signal_callback error:", e)

def main():
    # Build application
    app = ApplicationBuilder().token(TOKEN).build()
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("viewconfig", view_config))
    app.add_handler(CommandHandler("setconfig", set_config))
    # Schedule signal callback every 5 minutes
    app.job_queue.run_repeating(signal_callback, interval=300, first=0)
    # Start webhook server
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()