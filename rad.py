import os, urllib.parse, logging
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ الإعدادات ---
logging.basicConfig(level=logging.INFO)
flask_app = Flask('')
@flask_app.route('/')
def home(): return "🚀 System Stabilized"

def keep_alive():
    t = Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))))
    t.daemon = True; t.start()

# --- 🔑 البيانات ---
TOKEN = '8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc'
ADMINS = [6016547718]
SUPPORT = "https://t.me/HCICICVICIF9"

u_s, p_s = urllib.parse.quote_plus('Abduh'), urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{u_s}:{p_s}@cluster0.0a4wefx.mongodb.net/DragonFinal?retryWrites=true&w=majority"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    users_col = client.get_database()['investors']
except: users_col = None

# --- 🛠️ الوظائف ---
def get_u(uid):
    d = {"uid": int(uid), "sar": 0.0, "usd": 0.0, "t": 0}
    if users_col is None: return d
    res = users_col.find_one({"uid": int(uid)})
    return res if res else d

# --- 🏠 الواجهة الرئيسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (﷼)", callback_data='u_dep_sr'), InlineKeyboardButton("🇺🇸 استثمار ($)", callback_data='u_dep_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='u_w'), InlineKeyboardButton("📈 صفقاتي", callback_data='u_tr')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='u_wd')],
        [InlineKeyboardButton("👨‍💻 الدعم الفني", url=SUPPORT)]
    ]
    txt = "👑 **مرحباً بك في شركة سهم القابضة**\n\nاختر فئة الاستثمار لبدء العمل:"
    if update.message: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id; data = q.data
    await q.answer() # فك التعليق فوراً
    
    # قسم المستخدم (يبدأ بـ u_)
    if data == 'u_main': await start(update, context)
    elif data == 'u_w':
        u = get_u(uid)
        await q.edit_message_text(f"🏦 **رصيدك:**\n\n🇸🇦 `{u['sar']:,}` ﷼\n🇺🇸 `{u['usd']:,}` $", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='u_main')]]), parse_mode='Markdown')
    elif data == 'u_tr':
        u = get_u(uid)
        await q.edit_message_text(f"📈 **الصفقات:** `{u['t']}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='u_main')]]))
    elif data == 'u_wd':
        u = get_u(uid)
        r_s, r_u = u['sar']*0.2, u['usd']*0.2
        await q.edit_message_text(f"📤 **سحب الأرباح:**\n\nالرسوم (20%): `{r_s:,.1f}` ﷼ أو `{r_u:,.1f}` $\n\n**ادفع الرسوم لفتح البوابة.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='u_main')]]), parse_mode='Markdown')
    elif data.startswith('u_dep_'):
        curr = data.split('_')[2]
        vals = ["1000", "5000", "10000"] if curr == 'sr' else ["300", "1000", "5000"]
        btns = [[InlineKeyboardButton(f"{v}", callback_data=f"u_sel_{curr}_{v}")] for v in vals]
        btns.append([InlineKeyboardButton("🔙", callback_data='u_main')])
        await q.edit_message_text("📊 **اختر المبلغ:**", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith('u_sel_'):
        _, _, curr, amt = data.split('_')
        info = "الراجحي: `1234567890` باسم سهم القابضة" if curr == 'sr' else "USDT: `TLtLuhkU...`"
        await q.edit_message_text(f"✨ **إيداع {amt}:**\n\n{info}\n\n📸 **أرسل الإيصال الآن.**", parse_mode='Markdown')

    # قسم المالك (يبدأ بـ a_)
    elif data.startswith('a_'):
        if uid not in ADMINS: return
        # الصيغة: a_العملية_العملة_المبلغ_المعرف
        p = data.split('_')
        act, cur, amt, tid = p[1], p[2], p[3], p[4]
        if act == 'v':
            key = "sar" if cur == "sr" else "usd"
            if users_col: users_col.update_one({"uid": int(tid)}, {"$inc": {key: float(amt), "t": 1}}, upsert=True)
            await q.edit_message_caption("✅ تم الاعتماد!")
            try: await context.bot.send_message(tid, f"🎊 تم شحن `{amt}` في محفظتك!")
            except: pass
        else: await q.edit_message_caption("❌ تم الرفض.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text("⏳ جاري المراجعة...")
    # أزرار المالك (مختصرة جداً لضمان الاستجابة)
    def b(v, c): return InlineKeyboardButton(f"✅ {v}", callback_data=f"a_v_{c}_{v}_{u.id}")
    kb = [[b("1000", "sr"), b("5000", "sr")], [b("300", "us"), b("1000", "us")], [InlineKeyboardButton("❌ رفض", callback_data=f"a_x_0_0_{u.id}")]]
    for adm in ADMINS: await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع: {u.first_name}\nID: `{u.id}`", reply_markup=InlineKeyboardMarkup(kb))

if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    app.run_polling(drop_pending_updates=True)
