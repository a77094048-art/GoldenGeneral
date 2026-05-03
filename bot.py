import os, uuid, logging, asyncio, tempfile, shutil, glob
import requests
import yt_dlp
from flask import Flask, request
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8511885419:AAHi0yNNaA1IVDtulFZBokSb9l_KbXaQe38"
ADMIN_CHAT = "6829017835"
RENDER_URL = "https://goldengeneral.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

app = Flask(__name__)
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 أرسل رابط فيديو/صورة (فيسبوك، إنستغرام، تيك توك…) وسأحمله فورًا.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        url = "https://" + url
    msg = await update.message.reply_text("⏳ جاري التحميل...")
    tmp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = {
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            files = glob.glob(os.path.join(tmp_dir, '*'))
            if not files:
                await msg.edit_text("❌ لا وسائط.")
                return
            for file_path in files:
                size = os.path.getsize(file_path)
                if size < 50 * 1024 * 1024:
                    with open(file_path, 'rb') as f:
                        await update.message.reply_document(
                            document=InputFile(f),
                            filename=os.path.basename(file_path),
                            caption="تم التحميل ✅"
                        )
                else:
                    await update.message.reply_text("⚠️ الملف أكبر من 50 ميغا.")
        await msg.delete()
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

@app.route('/')
def health():
    return "GoldenDownloader is live"

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run(app_bot.process_update(update))
    return "OK"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(app_bot.initialize())
    requests.post(f"{TELEGRAM_URL}/setWebhook", json={"url": WEBHOOK_URL})
    logging.info(f"Webhook set to {WEBHOOK_URL}")
    app.run(host='0.0.0.0', port=PORT)