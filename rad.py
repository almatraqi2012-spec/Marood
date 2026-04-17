import os
import urllib.parse
import logging
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- ⚙️ 1. الإعدادات وسجلات النظام ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask('')
@flask_app.route('/')
def home(): return "🚀 Dragon Mega-System is Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask); t.daemon = True; t.start()

# --- 🔑 2. البيانات الحساسة وعناوين الشركة ---
TOKEN ='8731999916:AAHDjo1noyGIbUH699aTjNns9kCjP8P9SHc' 
ADMINS_LIST = [6016547718] 
SUPPORT_LINK = "https://t.me/HCICICVICIF9"

# 🏦 بيانات الدفع (عدلها بما يناسبك)
BANK_INFO = "🏦 **الحساب البنكي (الراجحي):**\n`123456789012345`\nالاسم: شركة التنين العالمية"
USDT_INFO = "🔗 **محفظة USDT (TRC20):**\n`TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA`"

# تشفير الدخول للقاعدة
u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonDB?retryWrites=true&w=majority&appName=Cluster0"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
users_col = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db = client.get_database()
    users_col = db['investors']
    client.admin.command('ping')
    logger.info("✅ Database Connected Successfully!")
except Exception as e:
    logger.error(f"❌ DB Error: {e}")

# --- 🛠️ 4. محرك العمليات ---
def get_user(uid):
    default = {"uid": int(uid), "sar": 0.0, "usd": 0.0, "trades": 0}
    if users_col is None: return default
    user = users_col.find_one({"uid": int(uid)})
    if not user:
        users_col.insert_one(default)
        return default
    return user

def add_funds(uid, curr, amt):
    field = "sar" if curr == "sr" else "usd"
    users_col.update_one({"uid": int(uid)}, {"$inc": {field: float(amt), "trades": 1}}, upsert=True)

# --- 🏠 5. واجهات البوت (الميزات الكاملة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    txt = (
        f"👑 **مرحباً بك في شركة التنين للاستثمار**\n\n"
        f"عزيزي المستثمر: **{user.first_name}**\n"
        f"نحن هنا لنأخذ استثماراتك إلى القمة.\n\n"
        "👇 **اختر من القائمة أدناه للبدء:**"
    )
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار ريال", callback_data='dep_sr'), InlineKeyboardButton("🇺🇸 استثمار دولار", callback_data='dep_us')],
        [InlineKeyboardButton("💳 محفظتي الشخصية", callback_data='wallet'), InlineKeyboardButton("📈 صفقاتي النشطة", callback_data='trades')],
        [InlineKeyboardButton("📤 طلب سحب أرباح", callback_data='withdraw')],
        [InlineKeyboardButton("👨‍💻 التواصل مع الدعم", url=SUPPORT_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(kb)
    if update.message: await update.message.reply_text(txt, reply_markup=reply_markup, parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(txt, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()

    if data == 'main': await start(update, context)

    elif data == 'wallet':
        u = get_user(uid)
        text = f"🏦 **تفاصيل حسابك:**\n\n💰 رصيد ريال: `{u.get('sar', 0):,}`\n💰 رصيد دولار: `{u.get('usd', 0):,}`"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'trades':
        u = get_user(uid)
        text = f"📈 **سجل العمليات:**\n\nعدد الصفقات النشطة: `{u.get('trades', 0)}`\nحالة السوق: 🟢 مستقر وتصاعدي"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'withdraw':
        await query.edit_message_text("📤 **طلب سحب:**\nيرجى كتابة المبلغ وتصوير محفظتك وإرسالها للدعم:\n" + SUPPORT_LINK, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]))

    elif data in ['dep_sr', 'dep_us']:
        curr = 'sr' if data == 'dep_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("📊 **اختر مبلغ الاستثمار المفضل:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        info = BANK_INFO if curr == 'sr' else USDT_INFO
        await query.edit_message_text(f"✨ **إيداع بقيمة {amt}:**\n\n{info}\n\n📸 **أرسل صورة الإيصال هنا فوراً ليتم تفعيل حسابك.**", parse_mode='Markdown')

    # --- إدارة الأزرار الذكية للمالك ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, curr, amt, tid = data.split('_')
            add_funds(tid, curr, amt)
            await query.edit_message_caption("✅ **تم الشحن بنجاح!**")
            try: await context.bot.send_message(chat_id=int(tid), text=f"🎊 **بشرى سارة!**\nتم تأكيد إيداعك بمبلغ `{amt}` وتفعيل صفقتك.")
            except: pass
        else: await query.edit_message_caption("❌ **تم رفض الإيصال.**")

async def on_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ **تم استلام إيصالك، جاري التدقيق من قبل الإدارة..**")
        # أزرار الإدارة المنظمة
        kb = [[InlineKeyboardButton(f"🇸🇦 {p}", callback_data=f"ok_sr_{p}_{user.id}") for p in PRICES_SAR[i:i+3]] for i in range(0, 6, 3)]
        kb += [[InlineKeyboardButton(f"💵 {p}$", callback_data=f"ok_us_{p}_{user.id}") for p in PRICES_USD[i:i+3]] for i in range(0, 6, 3)]
        kb.append([InlineKeyboardButton("🚫 رفض نهائي", callback_data=f"no_{user.id}")])
        
        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 **إيداع جديد:**\nالمستثمر: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(kb))

# --- 🚀 6. الانطلاق ---
if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, on_receipt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    
    logger.info("🔥 Dragon Final System is flying!")
    app.run_polling(drop_pending_updates=True)
