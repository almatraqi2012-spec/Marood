import logging
import os
import urllib.parse
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (لضمان استقرار البوت على Render ومنع الدوران) ---
server = Flask('')
@server.route('/')
def home(): return "🚀 Sahm Holding Platform is Online"

def run():
    server.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU' # تأكد من استخدام التوكن الجديد دائماً
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

# إعدادات المونغو المحدثة
u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('Abduh2026')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonFinal?authSource=admin&retryWrites=true&w=majority"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مبالغ الاستثمار الكاملة
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

def update_balance(uid, curr, amt):
    field = "bal_sar" if curr == "sr" else "bal_usd"
    users_col.update_one({"uid": uid}, {"$inc": {field: float(amt)}})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    keyboard = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    text = f"🏦 **المنصة العالمية للاستثمار**\n\nمرحباً بك سيد {user.first_name}\nاختر القسم المطلوب للبدء:"
    if update.message: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    elif data == 'wallet':
        u = get_user_data(uid)
        await query.edit_message_text(f"📊 **تفاصيل محفظتك:**\n\n🇸🇦 ريال: `{u['bal_sar']:,}`\n🇺🇸 دولار: `{u['bal_usd']:,}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    elif data == 'withdraw':
        u = get_user_data(uid)
        if u['bal_sar'] <= 0 and u['bal_usd'] <= 0:
            await query.edit_message_text("❌ محفظتك فارغة حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]))
        else:
            msg = f"📤 **إجراءات سحب الأرباح:**\n\n🇸🇦 رصيدك: `{u['bal_sar']:,}` ريال (الرسوم: `{u['bal_sar']*0.2:,}`)\n🇺🇸 رصيدك: `{u['bal_usd']:,}` دولار (الرسوم: `{u['bal_usd']*0.2:,}`)\n\n💡 الرسوم لفتح بوابة التحويل الدولي."
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {'ريال' if curr=='sr' else '$'}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        c_type = 'sr' if data.startswith('s_') else 'us'
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if c_type == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, c, a, target = data.split('_')
            update_balance(int(target), c, float(a))
            await query.edit_message_caption(caption=f"✅ تم تأكيد إيداع {a} {c}")
            try: await context.bot.send_message(int(target), f"🎉 تم إيداع `{a}` {c} في محفظتك بنجاح!")
            except: pass
        elif data.startswith('no_'):
            t = data.split('_')[1]
            await query.edit_message_caption(caption="❌ تم رفض الإيصال.")
            try: await context.bot.send_message(int(t), "❌ تم رفض الإيصال من قبل الإدارة.")
            except: pass

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ تم استلام الإيصال، جاري المراجعة...")
        # استعادة كامل أزرار المالك الـ 170 سطر
        def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
        kb = [
            [b("1000", "sr"), b("1500", "sr")], [b("2000", "sr"), b("3000", "sr")],
            [b("5000", "sr"), b("10000", "sr")], [b("20000", "sr"), b("50000", "sr")],
            [b("300", "us"), b("500", "us")], [b("1000", "us"), b("5000", "us")],
            [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
        ]
        for adm in ADMINS_LIST:
            try: await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع من: {user.first_name}\nID: `{user.id}`", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

if __name__ == '__main__':
    keep_alive() # تشغيل خادم الويب لمنع التعليق
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.run_polling(drop_pending_updates=True)
