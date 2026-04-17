import os
import urllib.parse
from flask import Flask
from threading import Thread
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. الإعدادات اللوجستية ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "💎 Dragon Investment System is Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. البيانات الأساسية (تعديل المحافظ هنا) ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMINS_LIST = [6016547718] 
SUPPORT_LINK = "https://t.me/HCICICVICIF9"

# 🏦 ضع معلوماتك الحقيقية هنا يا إمبراطور
BANK_DETAILS = "بنك الراجحي\nرقم الحساب: `123456789012345`\nالاسم: شركة التنين"
USDT_DETAILS = "شبكة TRC20\nالعنوان: `TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA`"

# تجميع رابط القاعدة بطريقة برمجية ذكية لتجنب أخطاء الرموز
user = urllib.parse.quote_plus('Abduh')
pw = urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{user}:{pw}@cluster0.0a4wefx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
users_col = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
    db = client['investment_platform']
    users_col = db['users']
    client.admin.command('ping')
    logger.info("✅ تم اختراق جدار الحماية والاتصال بنجاح!")
except Exception as e:
    logger.error(f"❌ خطأ في المصادقة: {e}")

# --- 🛠️ 4. محرك العمليات ---
def get_user_data(uid):
    if users_col is None: return {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
    user = users_col.find_one({"uid": int(uid)})
    if not user:
        user = {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    if users_col is None: return False
    field = "bal_sar" if curr == "sr" else "bal_usd"
    users_col.update_one({"uid": int(uid)}, {"$inc": {field: float(amt)}}, upsert=True)
    return True

# --- 🏠 5. الواجهة الرسومية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    welcome_text = (
        f"👑 **مرحباً بك في منصة التنين العالمية**\n\n"
        f"المستثمر: **{user.first_name}**\n"
        f"رقم العضوية: `{user.id}`\n\n"
        "💎 _اختر فئة الاستثمار لبدء رحلة النجاح:_"
    )
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (SAR)", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار (USDT)", callback_data='c_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='wallet'), InlineKeyboardButton("📊 صفقاتي", callback_data='trades')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='withdraw'), InlineKeyboardButton("👨‍💻 الدعم الفني", url=SUPPORT_LINK)]
    ]
    if update.message: await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    
    elif data == 'wallet':
        u = get_user_data(uid)
        text = f"🏦 **تفاصيل حسابك الاستثماري:**\n\n💰 رصيد الريال: `{u.get('bal_sar', 0):,}`\n💰 رصيد الدولار: `{u.get('bal_usd', 0):,}`"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['trades', 'withdraw']:
        msg = "📈 لا توجد صفقات نشطة." if data == 'trades' else f"📤 لطلب السحب تواصل مع الإدارة:\n{SUPPORT_LINK}"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        btns = [[InlineKeyboardButton(f"{p}", callback_data=f"sel_{curr}_{p}") for p in (PRICES_SAR if curr=='sr' else PRICES_USD)[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📊 **اختر مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        info = BANK_DETAILS if curr == 'sr' else USDT_DETAILS
        await query.edit_message_text(f"✨ **طلب إيداع بمبلغ {amt}**\n\nيرجى التحويل إلى:\n{info}\n\n📸 **أرسل صورة الإيصال هنا فوراً.**", parse_mode='Markdown')

    # --- 🛠️ نظام الإدارة الذكي ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, curr, amt, tid = data.split('_')
            if update_balance(tid, curr, amt):
                await query.edit_message_caption("✅ **تم الشحن بنجاح!**")
                try: await context.bot.send_message(chat_id=int(tid), text=f"🎊 **بشرى سارة!**\nتم تأكيد إيداعك بمبلغ `{amt}` بنجاح.")
                except: pass
        else:
            await query.edit_message_caption("❌ **تم رفض الإيصال.**")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ **تم استلام إيصالك، انتظر لحظات للتفعيل..**")
        
        kb_sr = [InlineKeyboardButton(f"🇸🇦 {p}", callback_data=f"ok_sr_{p}_{user.id}") for p in PRICES_SAR]
        kb_us = [InlineKeyboardButton(f"💵 {p}", callback_data=f"ok_us_{p}_{user.id}") for p in PRICES_USD]
        # تنظيم الأزرار بشكل 3 في كل صف
        admin_kb = [kb_sr[i:i+3] for i in range(0, 6, 3)] + [kb_us[i:i+3] for i in range(0, 6, 3)]
        admin_kb.append([InlineKeyboardButton("🚫 رفض الإيصال", callback_data=f"no_{user.id}")])

        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 **إيداع جديد:**\nمن: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(admin_kb))

if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    logger.info("🐉 Dragon Ultimate is Ready for Launch!")
    app.run_polling(drop_pending_updates=True)
