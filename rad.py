from flask import Flask
from threading import Thread
import logging
import sys
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 1. سيرفر Flask للبقاء حياً ---
flask_app = Flask('')
@flask_app.route('/')
def home(): return "🚀 إمبراطورية الدراجون تعمل بنجاح!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ⚙️ 2. إعدادات السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ⚙️ الإعدادات الأساسية ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718] 

# 💡 الرابط الذهبي الصحيح (المستخرج من حسابك مباشرة)
MONGO_URI = "mongodb+srv://Abduh:5D7NJi%25aAAkdRB@cluster0.0a4wefx.mongodb.net/investment_platform?retryWrites=true&w=majority&appName=Cluster0&authSource=admin"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. الاتصال بالقاعدة ---
users_col = None
try:
    client = MongoClient(MONGO_URI, connectTimeoutMS=30000, serverSelectionTimeoutMS=30000, tlsAllowInvalidCertificates=True)
    db = client['investment_platform']
    users_col = db['users']
    client.admin.command('ping')
    logger.info("✅ تم الاتصال بنجاح ساحق بالرابط الحقيقي!")
except Exception as e:
    logger.error(f"❌ فشل الاتصال: {e}")

# --- 🛠️ 4. الدوال الأساسية ---
def get_user_data(uid):
    if users_col is None: return {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
    uid_int = int(uid)
    user = users_col.find_one({"uid": uid_int})
    if not user:
        user = {"uid": uid_int, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    if users_col is None: return False
    try:
        uid_int = int(uid)
        field = "bal_sar" if curr == "sr" else "bal_usd"
        users_col.update_one({"uid": uid_int}, {"$inc": {field: float(amt)}}, upsert=True)
        return True
    except Exception as e:
        logger.error(f"❌ خطأ تحديث الرصيد: {e}")
        return False

# --- 🏠 5. الأوامر البرمجية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    
    welcome_text = (
        f"🙋‍♂️ **أهلاً بك يا سيد {user.first_name} في منصة التنين للاستثمار**\n\n"
        "🚀 **أنت الآن في المكان الصحيح لمضاعفة أرباحك.**\n"
        "نحن نوفر لك بيئة استثمارية آمنة، سريعة، وموثوقة.\n\n"
        "💎 **ابدأ رحلتك الآن باختيار الفئه الاستثمارية المفضلة لديك:**"
    )
    
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار بالريال", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار بالدولار", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي الشخصية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='withdraw'), InlineKeyboardButton("💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
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

    if data == 'main':
        await start(update, context)
    
    elif data == 'wallet':
        u = get_user_data(uid)
        wallet_text = (
            "📋 **تفاصيل محفظتك الاستثمارية:**\n\n"
            f"🇸🇦 الرصيد بالريال: `{u.get('bal_sar', 0):,}` ر.س\n"
            f"🇺🇸 الرصيد بالدولار: `{u.get('bal_usd', 0):,}` $\n\n"
            "⚠️ _يتم تحديث الرصيد تلقائياً بعد تأكيد الإيداع._"
        )
        await query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='main')]]), parse_mode='Markdown')
    
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        symbol = "ر.س" if curr == 'sr' else "$"
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {symbol}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📈 **اختر خطة الاستثمار المناسبة لك:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        method = "الحساب البنكي" if curr == 'sr' else "محفظة USDT (TRC20)"
        await query.edit_message_text(
            f"✅ **لقد اخترت استثمار مبلغ {amt}**\n\n"
            f"يرجى التحويل إلى {method}:\n"
            f"`{addr}`\n\n"
            "بعد التحويل، أرسل صورة الإيصال (Screenshot) هنا في الشات فوراً.",
            parse_mode='Markdown'
        )

    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        if data.startswith('ok_') and len(parts) == 5: # ok_sr_1000_id
            _, curr, amt, target_id = parts[0], parts[1], parts[2], parts[3]
            if update_balance(target_id, curr, amt):
                await query.edit_message_caption(caption=f"✅ تم الإيداع بنجاح!\nالمبلغ: {amt} {curr}\nللمستخدم: {target_id}")
                try: await context.bot.send_message(chat_id=int(target_id), text=f"🎉 **خبر سار!**\nتم تأكيد إيداعك بمبلغ `{amt}` {curr} ورصيدك الآن جاهز للاستثمار.")
                except: pass
        elif data.startswith('no_'):
            await query.edit_message_caption(caption="❌ تم رفض هذا الإيصال.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ **تم استلام الإيصال.**\nجاري المراجعة من قبل الإدارة، سيصلك إشعار فور التأكيد.")
        
        # أزرار الإدارة
        kb = []
        # تبسيط الأزرار للإدارة لضمان عدم الخطأ
        u_data = get_user_data(user.id)
        kb = [
            [InlineKeyboardButton("✅ تأكيد الإيداع", callback_data=f"ok_check_{user.id}")], # سيطلب المبلغ لاحقاً أو نثبته
            [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
        ]
        
        # ملاحظة: لتحسين الدقة، الإدمن يختار العملة والمبلغ عند التأكيد
        for admin in ADMINS_LIST:
            await context.bot.send_photo(
                chat_id=admin, 
                photo=update.message.photo[-1].file_id, 
                caption=f"🔔 **إشعار إيداع جديد**\n\nالمستثمر: {user.first_name}\nID: `{user.id}`\n\nيرجى التحقق ثم الضغط على زر التأكيد.", 
                reply_markup=InlineKeyboardMarkup(kb), 
                parse_mode='Markdown'
            )

# --- 🚀 6. تشغيل المحرك النهائي --
if __name__ == '__main__':
    keep_alive()
    
    # بناء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات (تأكد من وجودها جميعاً)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    # هذا السطر مهم جداً لاستقبال الصور
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    # هذا السطر لاستقبال أي رسالة نصية غير معروفة (للتجربة)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start)) 

    logger.info("🐉 الدراجون مستعد للتحليق...")
    
    # استخدام سطر تشغيل قوي يجبر التلجرام على البدء من اللحظة الحالية
    app.run_polling(drop_pending_updates=True, close_loop=False)
