import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات لمراقبة أداء البوت على السيرفر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '7885071515:AAEzZkVzA4iHcvn5GG9AXCsJTS2gIa-9UTc'
ADMIN_USERNAME = 'HCICICVICIF9'
MY_PERSONAL_ID = 6016547718

# رابط المونغو الخاص بك (تم دمجه وتحديثه للعمل السحابي)
MONGO_URI = "mongodb://alkreem12:Abn-alkreem12@cluster0-shard-00-00.p8iub.mongodb.net:27017,cluster0-shard-00-01.p8iub.mongodb.net:27017,cluster0-shard-00-02.p8iub.mongodb.net:27017/?tls=true&replicaSet=atlas-x13k9w-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

# --- 🗄️ الاتصال بقاعدة بيانات MongoDB ---
try:
    client = MongoClient(MONGO_URI)
    db = client['investment_platform']
    users_col = db['users']
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
            f"يرجى ارسال بياناتك هنا ثم اختر القسم المطلوب للبدء:")
    
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

    elif data.startswith('s_') or data.startswith('u_'):
        c_type = 'sr' if data.startswith('s_') else 'us'
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if c_type == 'sr' else CRYPTO_WALLET
        await query.edit_message_text(f"✅ تم اختيار {amt}\nحول إلى:\n`{addr}`\n\n📸 أرسل الإيصال هنا.", parse_mode='Markdown')

    elif data.startswith('ok_'):
        _, c, a, target = data.split('_')
        update_balance(int(target), c, float(a))
        await query.answer(f"✅ تمت إضافة {a} {c}", show_alert=True)
        try:
            await context.bot.send_message(chat_id=int(target), text=f"🎉 تم إيداع `{a}` {c} في محفظتك بنجاح!")
        except: pass

    elif data.startswith('no_'):
        t = data.split('_')[1]
        await query.answer("❌ تم الرفض")
        try:
            await context.bot.send_message(chat_id=int(t), text="❌ تم رفض الإيصال من قبل الإدارة.")
        except: pass

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        await update.message.reply_text("✅ تم استلام الإيصال، جاري المراجعة...")
        
        kb = [
            [InlineKeyboardButton("➕ 1000 ريال", callback_data=f"ok_sr_1000_{user.id}"), InlineKeyboardButton("➕ 100 $", callback_data=f"ok_us_100_{user.id}")],
            [InlineKeyboardButton("➕ 5000 ريال", callback_data=f"ok_sr_5000_{user.id}"), InlineKeyboardButton("➕ 500 $", callback_data=f"ok_us_500_{user.id}")],
            [InlineKeyboardButton("➕ 10000 ريال", callback_data=f"ok_sr_10000_{user.id}"), InlineKeyboardButton("➕ 1000 $", callback_data=f"ok_us_1000_{user.id}")],
            [InlineKeyboardButton("➕ 20000 ريال", callback_data=f"ok_sr_20000_{user.id}"), InlineKeyboardButton("➕ 5000 $", callback_data=f"ok_us_5000_{user.id}")],
            [InlineKeyboardButton("➕ 50000 ريال", callback_data=f"ok_sr_50000_{user.id}"), InlineKeyboardButton("➕ 20000 $", callback_data=f"ok_us_20000_{user.id}")],
            [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
        ]
        cap = f"🔔 **لوحة المالك**\nالاسم: {user.first_name}\nID: `{user.id}`\n\nاختر المبلغ المراد إضافته:"
        await context.bot.send_photo(chat_id=MY_PERSONAL_ID, photo=update.message.photo[-1].file_id, caption=cap, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

if __name__ == '__main__':
    # تشغيل البوت بنظام المعالجة المتوازية للسرعة القصوى
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    
    logger.info("🚀 المنصة تعمل بنظام المونغو السحابي والمبالغ الكاملة...")
    app.run_polling(drop_pending_updates=True)
