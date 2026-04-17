from flask import Flask
from threading import Thread
import logging
import os
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 تشغيل السيرفر الوهمي للبقاء حياً على Render ---
flask_app = Flask('')
@flask_app.route('/')
def home(): return "الدراجون يعمل بنجاح!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ⚙️ الإعدادات العامة ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] ================
TOKEN ='7885071515:AAEzZkVzA4iHcvn5GG9AXCsJTS2gIa-9UTc'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718] 

MONGO_URI = "mongodb+srv://Abduh:5D7NJi%25aAAkdRB@cluster0.p8iub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# القوائم التي سيتم صنع الأزرار منها آلياً
PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

# --- 🗄️ الاتصال بـ MongoDB ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['investment_platform']
    users_col = db['users']
    logger.info("✅ تم الاتصال بالمونغو")
except Exception as e:
    logger.error(f"❌ خطأ مونغو: {e}")

# --- 🛠️ الدوال البرمجية ---
def get_user_data(uid):
    user = users_col.find_one({"uid": uid})
    if not user:
        user = {"uid": uid, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    field = "bal_sar" if curr == "sr" else "bal_usd"
    users_col.update_one({"uid": uid}, {"$inc": {field: float(amt)}})

# --- 🏠 الواجهات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    kb = [
        [InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 دولار أمريكي", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي", callback_data='wallet'), InlineKeyboardButton("📤 سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    text = f"🏦 **مرحباً بك في المنصة العالمية**\n\nسيد {user.first_name}، اختر من القائمة للبدء:"
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
        text = f"📊 **تفاصيل محفظتك:**\n\n🇸🇦 ريال: `{u['bal_sar']:,}`\n🇺🇸 دولار: `{u['bal_usd']:,}`"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {('ر.س' if curr=='sr' else '$')}", callback_data=f"select_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('select_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\n\nحول المبلغ إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')

    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        try:
            if data.startswith('ok_'):
                _, curr, amt, target = data.split('_')
                update_balance(int(target), curr, amt)
                await query.edit_message_caption(caption=f"✅ تم تأكيد إيداع {amt} {curr} بنجاح.")
                try: await context.bot.send_message(chat_id=int(target), text=f"🎉 تم إضافة `{amt}` {curr} لمحفظتك!")
                except: pass
            elif data.startswith('no_'):
                await query.edit_message_caption(caption="❌ تم رفض هذا الإيصال.")
        except Exception as e: logger.error(f"خطأ زر المالك: {e}")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ جاري إرسال الإيصال للمالك...")
        
        # --- بناء لوحة الأزرار الكبيرة للمالك ---
        kb = []
        # أزرار الريال
        for i in range(0, len(PRICES_SAR), 2):
            row = [InlineKeyboardButton(f"🇸🇦 +{PRICES_SAR[i]}", callback_data=f"ok_sr_{PRICES_SAR[i]}_{user.id}")]
            if i+1 < len(PRICES_SAR): row.append(InlineKeyboardButton(f"🇸🇦 +{PRICES_SAR[i+1]}", callback_data=f"ok_sr_{PRICES_SAR[i+1]}_{user.id}"))
            kb.append(row)
        # أزرار الدولار
        for i in range(0, len(PRICES_USD), 2):
            row = [InlineKeyboardButton(f"💵 +{PRICES_USD[i]}$", callback_data=f"ok_us_{PRICES_USD[i]}_{user.id}")]
            if i+1 < len(PRICES_USD): row.append(InlineKeyboardButton(f"💵 +{PRICES_USD[i+1]}$", callback_data=f"ok_us_{PRICES_USD[i+1]}_{user.id}"))
            kb.append(row)
        
        kb.append([InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")])
        
        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 إيصال جديد من: {user.first_name}\nID: `{user.id}`\n\nاختر المبلغ للإضافة:", 
                                       reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    
    logger.info("🚀 الدراجون يعمل بأقصى طاقة...")
    app.run_polling(drop_pending_updates=True)
