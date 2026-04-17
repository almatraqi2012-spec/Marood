import os
from flask import Flask
from threading import Thread
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. الإعدادات والLogs ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "💎 Dragon Investment System is Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. البيانات الأساسية ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718] 

MONGO_URI = "mongodb+srv://Abduh:5D7NJi%25aAAkdRB@cluster0.0a4wefx.mongodb.net/investment_platform?retryWrites=true&w=majority&appName=Cluster0&authSource=admin"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
users_col = None
try:
    client = MongoClient(MONGO_URI, connectTimeoutMS=30000, serverSelectionTimeoutMS=30000, tlsAllowInvalidCertificates=True)
    db = client['investment_platform']
    users_col = db['users']
    logger.info("✅ Database Connected")
except Exception as e: logger.error(f"❌ DB Error: {e}")

# --- 🛠️ 4. محرك العمليات ---
def get_user_data(uid):
    if users_col is None: return None
    user = users_col.find_one({"uid": int(uid)})
    if not user:
        user = {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    if users_col is None: return False
    try:
        field = "bal_sar" if curr == "sr" else "bal_usd"
        users_col.update_one({"uid": int(uid)}, {"$inc": {field: float(amt)}}, upsert=True)
        return True
    except Exception as e: return False

# --- 🏠 5. الواجهة والأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    
    welcome_text = (
        f"👑 **مرحباً بك في منصة التنين العالمية**\n\n"
        f"السيد: **{user.first_name}**\n"
        "يسعدنا انضمامك لبيئة الاستثمار الأكثر أماناً.\n\n"
        "💡 **يرجى اختيار فئة الاستثمار لبدء جني الأرباح:**"
    )
    
    kb = [
        [InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 دولار أمريكي", callback_data='c_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='wallet'), InlineKeyboardButton("📈 صفقاتي", callback_data='trades')],
        [InlineKeyboardButton("📤 سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("👨‍💻 التواصل مع الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    
    elif data == 'wallet':
        u = get_user_data(uid)
        text = (
            "🏦 **حالة محفظتك الاستثمارية**\n\n"
            f"💰 رصيد الريال: `{u.get('bal_sar', 0):,}` ر.س\n"
            f"💰 رصيد الدولار: `{u.get('bal_usd', 0):,}` $\n\n"
            "🛡️ _أموالك مؤمنة بنظام التشفير العالمي._"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]), parse_mode='Markdown')
    
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        symbol = "ر.س" if curr == 'sr' else "$"
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {symbol}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📊 **اختر مبلغ الاستثمار المخصص:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        method = "الحساب البنكي" if curr == 'sr' else "محفظة USDT"
        await query.edit_message_text(
            f"✨ **تفاصيل عملية الإيداع ({amt})**\n\n"
            f"يرجى التحويل إلى {method}:\n"
            f"`{addr}`\n\n"
            "📸 **بعد التحويل، يرجى إرسال صورة الإيصال هنا لرفع الرصيد.**",
            parse_mode='Markdown'
        )

    # --- إدارة الأزرار الذكية للمالك ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        if parts[0] == 'ok':
            _, curr, amt, target_id = parts
            if update_balance(target_id, curr, amt):
                await query.edit_message_caption(caption=f"✅ **تم الإيداع بنجاح**\nالمبلغ: {amt}\nالمستثمر: {target_id}")
                try: await context.bot.send_message(chat_id=int(target_id), text=f"🎊 **تهانينا!**\nتم تأكيد إيداعك بمبلغ `{amt}` بنجاح.\nرصيدك الآن جاهز للاستثمار.")
                except: pass
        else:
            await query.edit_message_caption(caption="❌ **تم رفض الإيصال من قبل الإدارة.**")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ **جاري مراجعة إيصالك من قبل الإدارة..**\nسيصلك إشعار فور التأكيد.")
        
        # إنشاء لوحة تحكم ذكية للمالك بضغطة واحدة
        kb_sr = [InlineKeyboardButton(f"🇸🇦 {p}", callback_data=f"ok_sr_{p}_{user.id}") for p in PRICES_SAR]
        kb_us = [InlineKeyboardButton(f"💵 {p}$", callback_data=f"ok_us_{p}_{user.id}") for p in PRICES_USD]
        
        # تنظيم الأزرار بشكل احترافي
        admin_kb = [kb_sr[i:i+3] for i in range(0, len(kb_sr), 3)] + [kb_us[i:i+3] for i in range(0, len(kb_us), 3)]
        admin_kb.append([InlineKeyboardButton("🚫 رفض وإلغاء", callback_data=f"no_{user.id}")])

        for admin in ADMINS_LIST:
            await context.bot.send_photo(
                chat_id=admin, 
                photo=update.message.photo[-1].file_id, 
                caption=f"🔔 **إيصال جديد للاعتماد**\nالمستثمر: {user.first_name}\nID: `{user.id}`\n\nاضغط على المبلغ للإضافة المباشرة:", 
                reply_markup=InlineKeyboardMarkup(admin_kb), 
                parse_mode='Markdown'
            )

# --- 🚀 6. التشغيل النهائي ---
if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    
    logger.info("🐉 Dragon Elite Bot is Flying...")
    app.run_polling(drop_pending_updates=True) 
