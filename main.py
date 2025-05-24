# main.py (Webhook + JobQueue)
import os, json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)
from analyzer import analyze_last_candle

# --- تنظیمات ---
TOKEN        = "7599460125:AAENWUkKQceP9O9kZn8y1SGQzaczmPpZWsA"
PORT         = int(os.environ.get("PORT", "10000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL  = f"https://telegram-tradebot.onrender.com{WEBHOOK_PATH}"
CONFIG_FILE  = "config.json"
CHAT_ID_FILE = "chat_id.txt"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

# --- فرمان‌های تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ذخیره chat_id
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ Bot is live via Webhook.")

async def view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    text = (
        f"Current Config:\n"
        f"a = {cfg['a']}\n"
        f"b = {cfg['b']}\n"
        f"combos = {cfg['combos']}"
    )
    await update.message.reply_text(text)

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        a = float(args[0]); b = float(args[1])
        combos = [tuple(map(int, x.split(","))) for x in args[2:]]
        save_config({"a": a, "b": b, "combos": combos})
        await update.message.reply_text("✅ Config updated.")
    except:
        await update.message.reply_text(
            "❌ Invalid format. Use:\n"
            "/setconfig 1 1 3,8 3,10 3,11"
        )

# --- تابع سیگنال‌دهی برای JobQueue ---
async def signal_callback(context: CallbackContext):
    cfg = load_config()
    result = analyze_last_candle(cfg["a"], cfg["b"], cfg["combos"])
    if result:
        with open(CHAT_ID_FILE, "r") as f:
            chat_id = int(f.read().strip())
        text = (
            f"📈 Signal: {result['direction'].upper()}\n"
            f"Entry:   {result['entry']:.2f}\n"
            f"TP:      {result['tp']:.2f}\n"
            f"SL:      {result['sl']:.2f}\n"
            f"Leverage:{result['leverage']}x"
        )
        await context.bot.send_message(chat_id=chat_id, text=text)

# --- نقطه‌ی ورود ---
def main():
    # ۱) ساخت Application با JobQueue
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .job_queue()      # ← حتماً این خط
        .build()
    )

    # ۲) ثبت فرمان‌ها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("viewconfig", view_config))
    app.add_handler(CommandHandler("setconfig", set_config))

    # ۳) برنامه‌ریزی اجرا در JobQueue
    #    هر ۳۰۰ ثانیه (۵ دقیقه) اولین اجرا بلافاصله
    app.job_queue.run_repeating(signal_callback, interval=300, first=0)

    # ۴) ست کردن Webhook در تلگرام
    #    دقت کن این تابع یک coroutine است و باید await شود
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        app.bot.set_webhook(WEBHOOK_URL)
    )

    # ۵) اجرای وبهوک (بلوک‌کننده)
    app.run_webhook(
        listen=      "0.0.0.0",
        port=        PORT,
        path=        WEBHOOK_PATH,
        webhook_url= WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()
