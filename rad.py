import logging
import os
import urllib.parse
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- خادم الويب (إجباري لـ Render) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Bot is Online"

def run():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# --- إعدادات المونغو ---
u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('Abduh2026')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonFinal?authSource=admin&retryWrites=true&w=majority"

# الاتصال بالقاعدة
client = MongoClient(MONGO_URI)
db = client['investment_platform']
users_col = db['users']

# الإعدادات
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMINS_LIST = [6016547718]
PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]

# دالة الحصول على البيانات
def get_user(uid):
    u = users_col.find_one({"uid": uid})
    if not u:
        u = {"uid": uid, "bal_sar": 0.0, "bal_usd": 0.0}
        users_col.insert_one(u)
    return u

# --- الدوال الأساسية (التي كانت شغالة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار ريال", callback_data='c_sr'), InlineKeyboardButton("🇺🇸 استثمار دولار", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي", callback_data='wallet')],
        [InlineKeyboardButton("📤 سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 الإدارة", url="https://t.me/HCICICVICIF9")]
    ]
    msg = f"🏦 مرحباً بك في شركة سهم القابضة\n\nاختر من القائمة:"
    if update.message: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    else: await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    elif data == 'wallet':
        u = get_user(uid)
        await query.edit_message_text(f"📊 محفظتك:\n\n﷼: {u['bal_sar']}\n$: {u['bal_usd']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]))
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        p_list = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in p_list[i:i+2]] for i in range(0, len(p_list), 2)]
        btns.append([InlineKeyboardButton("🔙", callback_data='main')])
        await query.edit_message_text("🏦 اختر المبلغ:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول المبلغ وأرسل الإيصال هنا.")
    # أزرار المالك (التأكيد والرفض)
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')
        if data.startswith('ok_'):
            users_col.update_one({"uid": int(parts[3])}, {"$inc": {f"bal_{'sar' if parts[1]=='sr' else 'usd'}": float(parts[2])}})
            await query.edit_message_caption("✅ تم التأكيد")
        else: await query.edit_message_caption("❌ تم الرفض")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # أزرار المالك الكاملة كما طلبت
    def b(v, c): return InlineKeyboardButton(f"➕ {v} {('﷼' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
    kb = [
        [b("1000", "sr"), b("1500", "sr")], [b("2000", "sr"), b("3000", "sr")],
        [b("5000", "sr"), b("10000", "sr")], [b("300", "us"), b("1000", "us")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"no_{user.id}")]
    ]
    for adm in ADMINS_LIST:
        await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع من {user.first_name}", reply_markup=InlineKeyboardMarkup(kb))

if __name__ == '__main__':
    Thread(target=run).start() # تشغيل السيرفر
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(drop_pending_updates=True)
