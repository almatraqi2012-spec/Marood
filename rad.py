from flask import Flask
from threading import Thread
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 1. سيرفر Flask ---
flask_app = Flask('')
@flask_app.route('/')
def home(): return "بوابة الإمبراطور تعمل!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ⚙️ 2. الإعدادات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN ='7885071515:AAEzZkVzA4iHcvn5GG9AXCsJTS2gIa-9UTc'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718] 

MONGO_URI = "mongodb+srv://Abduh:5D7NJi%25aAAkdRB@cluster0.p8iub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]

# --- 🗄️ 3. المونغو ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['investment_platform']
    users_col = db['users']
except Exception as e:
    logger.error(f"❌ خطأ مونغو: {e}")

# --- 🛠️ 4. الدوال الأساسية (تم تعديلها لتعمل مثل النسخ القديمة) ---
def get_user_data(uid):
    uid_int = int(uid)
    user = users_col.find_one({"uid": uid_int})
    if not user:
        user = {"uid": uid_int, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    try:
        uid_int = int(uid)
        amt_float = float(amt)
        field = "bal_sar" if curr == "sr" else "bal_usd"
        
        # نستخدم upsert=True لضمان إنشاء السجل إذا لم يكن موجوداً
        result = users_col.update_one(
            {"uid": uid_int}, 
            {"$inc": {field: amt_float}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"💥 فشل تحديث الرصيد: {e}")
        return False

# --- 🏠 5. الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    kb = [
        [InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 دولار أمريكي", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي", callback_data='wallet'), InlineKeyboardButton("📤 سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    text = f"🏦 **مرحباً بك سيد {user.first_name}**\nاختر فئة الاستثمار:"
    if update.message: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    elif data == 'wallet':
        u = get_user_data(uid)
        text = f"📊 **محفظتك:**\n\n🇸🇦: `{u.get('bal_sar', 0):,}` ريال\n🇺🇸: `{u.get('bal_usd', 0):,}` دولار"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {('ر.س' if curr=='sr' else '$')}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙", callback_data='main')])
        await query.edit_message_text("🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ اخترت {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')

    # --- 🛠️ الجزء الحساس: أزرار المالك ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        
        if data.startswith('ok_') and len(parts) == 4:
            _, curr, amt, target_id = parts
            # محاولة الإضافة
            if update_balance(target_id, curr, amt):
                await query.edit_message_caption(caption=f"✅ تم بنجاح إضافة {amt} {curr} للمستثمر.")
                try: 
                    await context.bot.send_message(chat_id=int(target_id), text=f"🎉 **إيداع ناجح!** تم إضافة `{amt}` {curr} لمحفظتك.", parse_mode='Markdown')
                except: pass
            else:
                await query.answer("❌ فشل تقني في الإضافة للقاعدة!", show_alert=True)
                
        elif data.startswith('no_'):
            await query.edit_message_caption(caption="❌ تم الرفض.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ جاري المراجعة...")
        
        kb = []
        for p in PRICES_SAR: kb.append([InlineKeyboardButton(f"🇸🇦 +{p}", callback_data=f"ok_sr_{p}_{user.id}")])
        for p in PRICES_USD: kb.append([InlineKeyboardButton(f"💵 +{p}$", callback_data=f"ok_us_{p}_{user.id}")])
        kb.append([InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")])
        
        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 إيصال من: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

if __name__ == '__main__':
    try:
        keep_alive()
        # إضافة إعدادات إضافية لضمان عدم حدوث Conflict
        app = Application.builder().token(TOKEN).concurrent_updates(True).build()
        
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
        
        logger.info("🚀 الدراجون انطلق الآن..")
        # سطر التشغيل الذهبي:
        app.run_polling(drop_pending_updates=True, stop_signals=None)
    except Exception as e:
        logger.error(f"💥 خطأ كارثي أثناء التشغيل: {e}")
