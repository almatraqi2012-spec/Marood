import os
from flask import Flask
from threading import Thread
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. إعدادات السجلات (Logs) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 🌐 2. سيرفر Flask للبقاء حياً على Render ---
flask_app = Flask('')

@flask_app.route('/')
def home(): 
    return "🚀 إمبراطورية الدراجون تعمل بنجاح!"

def run_flask():
    # استخدام المنفذ الذي يطلبه رندر أو 10000 كافتراضي
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ⚙️ 3. الإعدادات الأساسية (التوكن والروابط) ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718] 

# الرابط الحقيقي الذي استخرجه الإمبراطور
MONGO_URI = "mongodb+srv://Abduh:5D7NJi%25aAAkdRB@cluster0.0a4wefx.mongodb.net/investment_platform?retryWrites=true&w=majority&appName=Cluster0&authSource=admin"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 4. الاتصال بالقاعدة ---
users_col = None
try:
    client = MongoClient(MONGO_URI, connectTimeoutMS=30000, serverSelectionTimeoutMS=30000, tlsAllowInvalidCertificates=True)
    db = client['investment_platform']
    users_col = db['users']
    client.admin.command('ping')
    logger.info("✅ تم الاتصال بنجاح بقاعدة البيانات!")
except Exception as e:
    logger.error(f"❌ خطأ في القاعدة: {e}")

# --- 🛠️ 5. الدوال المساعدة ---
def get_user_data(uid):
    if users_col is None: return {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
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
    except Exception as e:
        logger.error(f"❌ خطأ تحديث الرصيد: {e}")
        return False

# --- 🏠 6. معالجات الأوامر (Handlers) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    
    welcome_text = (
        f"🙋‍♂️ **أهلاً بك يا سيد {user.first_name} في منصة التنين للاستثمار**\n\n"
        "🚀 **أنت الآن في المكان الصحيح لمضاعفة أرباحك.**\n"
        "نحن نوفر لك بيئة استثمارية آمنة، سريعة، وموثوقة.\n\n"
        "💎 **ابدأ رحلتك الآن باختيار العملة المفضلة لديك:**"
    )
    
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار بالريال", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار بالدولار", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي الشخصية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='withdraw'), InlineKeyboardButton("💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    
    markup = InlineKeyboardMarkup(kb)
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main':
        await start(update, context)
    
    elif data == 'wallet':
        u = get_user_data(uid)
        text = (
            "📋 **تفاصيل محفظتك:**\n\n"
            f"🇸🇦 رصيدك: `{u.get('bal_sar', 0):,}` ر.س\n"
            f"🇺🇸 رصيدك: `{u.get('bal_usd', 0):,}` $\n"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        symbol = "ر.س" if curr == 'sr' else "$"
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {symbol}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📈 **اختر مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ **تم اختيار استثمار {amt}**\n\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')

    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        if parts[0] == 'ok':
            # تنسيق الداتا: ok_العملة_المبلغ_الأيدي
            _, curr, amt, target_id = parts
            if update_balance(target_id, curr, amt):
                await query.edit_message_caption(caption=f"✅ تم تأكيد {amt} للمستخدم {target_id}")
                try: await context.bot.send_message(chat_id=int(target_id), text=f"🎉 تم إضافة `{amt}` لمحفظتك بنجاح!")
                except: pass
        else:
            await query.edit_message_caption(caption="❌ تم رفض الإيصال.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ **تم استلام الإيصال، انتظر التأكيد.**")
        
        # أزرار الإدارة للموافقة السريعة (مثال على مبلغ 1000)
        kb = [
            [InlineKeyboardButton("✅ تأكيد 1000 ريال", callback_data=f"ok_sr_1000_{user.id}")],
            [InlineKeyboardButton("✅ تأكيد 300 دولار", callback_data=f"ok_us_300_{user.id}")],
            [InlineKeyboardButton("❌ رفض", callback_data=f"no_{user.id}")]
        ]
        
        for admin in ADMINS_LIST:
            await context.bot.send_photo(
                chat_id=admin, 
                photo=update.message.photo[-1].file_id, 
                caption=f"🔔 إيداع جديد من: {user.first_name}\nID: `{user.id}`", 
                reply_markup=InlineKeyboardMarkup(kb), 
                parse_mode='Markdown'
            )

# --- 🚀 7. التشغيل النهائي ---
if __name__ == '__main__':
    keep_alive() # تشغيل سيرفر Flask
    
    app = Application.builder().token(TOKEN).build()
    
    # المعالجات
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start)) # للرد على أي نص بالترحيب

    logger.info("🐉 الدراجون مستعد للتحليق...")
    app.run_polling(drop_pending_updates=True)
