import logging
import os
import sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (لضمان بقاء البوت حياً على Render) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🚀 Sahm Platform is Online and Stable"

def run_server():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

PRICES_SAR = ["1000", "1500", "2000", "3000", "5000", "7000", "8000", "10000", "15000", "20000", "30000", "50000"]
PRICES_USD = ["300", "400", "500", "600", "800", "1000", "2000", "3000", "5000", "20000", "30000"]
# ===============================================================

# --- 🗄️ إدارة قاعدة البيانات المحلية (SQLite) ---
def init_db():
    conn = sqlite3.connect('investment.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY,
            bal_sar REAL DEFAULT 0.0,
            bal_usd REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    return conn

db_conn = init_db()

def get_user_data(uid):
    cursor = db_conn.cursor()
    cursor.execute('SELECT bal_sar, bal_usd FROM users WHERE uid = ?', (uid,))
    row = cursor.fetchone()
    if not row:
        cursor.execute('INSERT INTO users (uid, bal_sar, bal_usd) VALUES (?, 0.0, 0.0)', (uid,))
        db_conn.commit()
        return {"bal_sar": 0.0, "bal_usd": 0.0}
    return {"bal_sar": row[0], "bal_usd": row[1]}

def update_balance(uid, curr, amt):
    cursor = db_conn.cursor()
    field = "bal_sar" if curr == 'sr' else "bal_usd"
    cursor.execute(f'UPDATE users SET {field} = {field} + ? WHERE uid = ?', (float(amt), int(uid)))
    db_conn.commit()

# --- 🏠 دالة البداية (Start) ---
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
    text = f"🏦 **مرحباً بك في شركة العالميه للأستثمار**\n\nالسيد: {user.first_name}\nيرجى إرسال بياناتك هنا ثم أختار الفئة الاستثماريه المناسبه لك للبدء:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- 🔘 معالج الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    elif data == 'wallet':
        u = get_user_data(uid)
        await query.edit_message_text(f"📊 **محفظتك المالية:**\n\n🇸🇦: `{u['bal_sar']:,}` ﷼\n🇺🇸: `{u['bal_usd']:,}` $", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data == 'withdraw':
        u = get_user_data(uid)
        msg = f"📤 **طلب سحب الأرباح**\n\nرصيدك المتاح:\n🇸🇦: {u['bal_sar']} ﷼\n🇺🇸: {u['bal_usd']} $\n\n💡 ملاحظة: رسوم فتح بوابة التحويل هي 20%."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data='main')]]), parse_mode='Markdown')
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = PRICES_SAR if curr == 'sr' else PRICES_USD
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙", callback_data='main')])
        await query.edit_message_text("🏦 اختر مبلغ الاستثمار المطلوب:", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ اخترت مبلغ {amt}\nحول المبلغ إلى:\n`{addr}`\n\n📸 أرسل إيصال التحويل هنا كصورة.", parse_mode='Markdown')
    
    # --- أزرار المالك ---
    elif data.startswith('ok_'):
        if uid not in ADMINS_LIST: return
        try:
            _, cur, val, tid = data.split('_')
            update_balance(tid, cur, val)
            await query.edit_message_caption(caption=f"✅ تم تأكيد إيداع {val} {cur} للمستخدم `{tid}`")
            await context.bot.send_message(chat_id=int(tid), text=f"🎉 أبشر.. تم إيداع `{val}` {cur} في محفظتك بنجاح!")
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.answer("❌ فشل الإيداع")
    elif data.startswith('no_'):
        if uid not in ADMINS_LIST: return
        tid = data.split('_')[1]
        await query.edit_message_caption(caption="❌ تم رفض الإيصال من قبل الإدارة.")
        try: await context.bot.send_message(chat_id=int(tid), text="❌ نعتذر، تم رفض الإيصال من قبل الإدارة.")
        except: pass

# --- 📸 معالج الصور ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ استلمنا الإيصال، جاري المراجعة...")
    
    def b(v, c): return InlineKeyboardButton(f"➕ {v} {('﷼' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
    
    kb = [
        [b("1000", "sr"), b("1500", "sr")], [b("2000", "sr"), b("3000", "sr")],
        [b("5000", "sr"), b("10000", "sr")], [b("300", "us"), b("1000", "us")],
        [InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"no_{user.id}")]
    ]
    
    for adm in ADMINS_LIST:
        try:
            await context.bot.send_photo(chat_id=adm, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 إيداع جديد:\nالاسم: {user.first_name}\nID: `{user.id}`", 
                                       reply_markup=InlineKeyboardMarkup(kb))
        except: pass

if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("🚀 البوت انطلق بنظام الذاكرة الداخلية..")
    app.run_polling(drop_pending_updates=True)
