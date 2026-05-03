import os, uuid, logging, asyncio, tempfile, shutil, glob
import requests
import yt_dlp
from flask import Flask
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from threading import Thread

# ========== القيم المدمجة ==========
BOT_TOKEN = "8511885419:AAHi0yNNaA1IVDtulFZBokSb9l_KbXaQe38"
ADMIN_CHAT = "6829017835"
RENDER_URL = "https://goldengeneral.onrender.com"
PORT = int(os.environ.get("PORT", 10000))
LOGO_PATH = "/app/logo.PNG"   # تم التعديل ليطابق الاسم في المستودع
# ===================================

app = Flask(__name__)
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "🏅 **بوت الجنرال الذهبي - المحمِّل الأسطوري**\n\n"
        "🎥 أرسل رابط فيديو أو صورة من أي منصة تواصل اجتماعي\n"
        "وسأقوم بتحميله وإرساله إليك فورًا.\n\n"
        "المنصات المدعومة: فيسبوك، إنستغرام، تيك توك، تويتر… والمزيد."
    )
    # إرسال الصورة أولاً إن وُجِدت
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as img:
            await update.message.reply_photo(
                photo=InputFile(img),
                caption=caption,
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

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
            'socket_timeout': 30,
            'retries': 3,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        files = glob.glob(os.path.join(tmp_dir, '*'))
        if not files:
            await msg.edit_text("❌ لم أجد وسائط.")
            return
        for file_path in files:
            size = os.path.getsize(file_path)
            if size < 50 * 1024 * 1024:
                with open(file_path, 'rb') as f:
                    await update.message.reply_document(
                        document=InputFile(f),
                        filename=os.path.basename(file_path),
                        caption="✅ تم التحميل"
                    )
            else:
                await update.message.reply_text("⚠️ الملف كبير ولن يُرسل.")
        await msg.delete()
    except Exception as e:
        logging.exception("Download error")
        await msg.edit_text(f"❌ فشل التحميل:\n{e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

@app.route('/')
def health():
    return "GoldenDownloader is live"

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_bot.run_polling(stop_signals=[], close_loop=False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT)
