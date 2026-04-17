import os
from flask import Flask
from threading import Thread
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. إعدادات النظام ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "💎 Dragon Platform is Running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. الإعدادات الأساسية (عدل العناوين هنا) ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMINS_LIST = [6016547718] 
SUPPORT_LINK = "https://t.me/HCICICVICIF9"

# 🚩 ضع عناوينك هنا يا غالي:
BANK_ACCOUNT = "الراجحي: 123456789012345" # ضع رقم حسابك البنكي هنا
USDT_ADDRESS = "TRC20: TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # ضع عنوان محفظتك هنا

MONGO_URI = "mongodb+srv://Abduh:A11223344%405566@cluster0.0a4wefx.mongodb.net/investment_platform?retryWrites=true&w=majority&appName=Cluster0"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
users_col = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client['investment_platform']
    users_col = db['users']
    client.admin.command('ping')
    logger.info("✅ Database Connected")
except Exception as e: logger.error(f"❌ DB Error: {e}")

# --- 🛠️ 4. العمليات ---
def get_user_data(uid):
    if users_col is None: return {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
    user = users_col.find_one({"uid": int(uid)})
    if not user:
        user = {"uid": int(uid), "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    field = "bal_sar" if curr == "sr" else "bal_usd"
    users_col.update_one({"uid": int(uid)}, {"$inc": {field: float(amt)}}, upsert=True)
    return True

# --- 🏠 5. الواجهة ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    text = f"👑 **أهلاً بك في منصة التنين العالمية**\n\nالسيد: **{user.first_name}**\nرقم العضوية: `{user.id}`\n\n💡 **اختر العملية المطلوبة:**"
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار ريال", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار دولار", callback_data='c_us')],
        [InlineKeyboardButton("💳 محفظتي", callback_data='wallet'), InlineKeyboardButton("📈 صفقاتي", callback_data='trades')],
        [InlineKeyboardButton("📤 طلب سحب", callback_data='withdraw'), InlineKeyboardButton("👨‍💻 الدعم", url=SUPPORT_LINK)]
    ]
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
        text = f"🏦 **تفاصيل محفظتك:**\n\n🇸🇦 ريال: `{u.get('bal_sar', 0):,}`\n🇺🇸 دولار: `{u.get('bal_usd', 0):,}`"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'trades':
        await query.edit_message_text("📈 **لا توجد صفقات نشطة حالياً.**\nابدأ الإيداع لتفعيل صفقاتك.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]))

    elif data == 'withdraw':
        await query.edit_message_text("📤 **لطلب السحب، يرجى التواصل مع المدير المالي مباشرة:**\n" + SUPPORT_LINK, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]))

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📊 **اختر مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        addr = BANK_ACCOUNT if curr == 'sr' else USDT_ADDRESS
        await query.edit_message_text(f"✨ **إيداع مبلغ {amt}**\n\nيرجى التحويل إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا فوراً.", parse_mode='Markdown')

    # --- 🛠️ إدارة الأزرار (إصلاح الاستجابة) ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        if parts[0] == 'ok':
            _, curr, amt, target_id = parts
            if update_balance(target_id, curr, amt):
                await query.edit_message_caption(caption=f"✅ تم اعتماد {amt} للآيدي {target_id}")
                try: await context.bot.send_message(chat_id=int(target_id), text=f"🎊 مبروك! تم شحن حسابك بمبلغ `{amt}`.")
                except: pass
        else:
            await query.edit_message_caption(caption="❌ تم رفض هذا الإيصال.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ تم استلام إيصالك، انتظر التفعيل..")
        kb_sr = [InlineKeyboardButton(f"🇸🇦 {p}", callback_data=f"ok_sr_{p}_{user.id}") for p in PRICES_SAR]
        kb_us = [InlineKeyboardButton(f"💵 {p}$", callback_data=f"ok_us_{p}_{user.id}") for p in PRICES_USD]
        admin_kb = [kb_sr[i:i+3] for i in range(0, 6, 3)] + [kb_us[i:i+3] for i in range(0, 6, 3)]
        admin_kb.append([InlineKeyboardButton("🚫 رفض الإيصال", callback_data=f"no_{user.id}")])
        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 إيداع جديد\nمن: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(admin_kb))

if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    logger.info("🐉 Dragon Ultimate is Ready!")
    app.run_polling(drop_pending_updates=True)
