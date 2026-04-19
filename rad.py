import logging, os, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- خادم الويب (لضمان بقاء السيرفر حياً) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🚀 Sahm Platform Running"

def run_server():
    app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# إعدادات الإمبراطور
TOKEN = '8731999916:AAHdeigVSmil8KD6GeA7OazVZkjVxhq9QJU'
ADMINS = [6016547718]
ADMIN_USERNAME = 'HCICICVICIF9'

# --- إدارة قاعدة البيانات (SQLITE المستقرة) ---
def get_db():
    conn = sqlite3.connect('sahm_final_v3.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, sar REAL DEFAULT 0, usd REAL DEFAULT 0)')
    return conn

db = get_db()

def update_bal(uid, curr, amt):
    field = "sar" if curr == 'sr' else "usd"
    db.execute(f"UPDATE users SET {field} = {field} + ? WHERE uid = ?", (float(amt), int(uid)))
    db.commit()

def get_bal(uid):
    row = db.execute("SELECT sar, usd FROM users WHERE uid = ?", (uid,)).fetchone()
    if not row:
        db.execute("INSERT INTO users VALUES (?, 0, 0)", (uid,))
        db.commit()
        return 0.0, 0.0
    return row

# --- 🏠 دالة البداية (Start) بنسقها السابق ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_bal(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🇸🇦 استثمار (بالريال السعودي)", callback_data='c_sr'),
         InlineKeyboardButton("🇺🇸 استثمار (بالدولار)", callback_data='c_us')],
        [InlineKeyboardButton("🌍 الاستثمار بعملات أخرى", callback_data='other_currency')],
        [InlineKeyboardButton("💰 محفظتي المالية", callback_data='wallet')],
        [InlineKeyboardButton("📤 طلب سحب الأرباح", callback_data='withdraw')],
        [InlineKeyboardButton("💬 التواصل مع الإدارة", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    
    text = (f"🏦 **المنصة العالمية للاستثمار (شركة سهم)**\n\n"
            f"مرحباً بك سيد {user.first_name}\n"
            f"يرجى اختيار القسم المطلوب للبدء:")
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- 🔘 معالج الأزرار ---
async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data, uid = q.data, q.from_user.id
    await q.answer()

    if data == 'main': 
        await start(update, context)
    
    elif data == 'other_currency':
        text = "🌍 **الاستثمار بالعملات الدولية:**\n\nيرجى التواصل مع الدعم الفني للحصول على حساباتنا البنكية من أي دولة في العالم."
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data == 'wallet':
        s, u = get_bal(uid)
        text = f"📊 **تفاصيل محفظتك المالية:**\n\n🇸🇦 ريال سعودي: `{s:,}`\n🇺🇸 دولار أمريكي: `{u:,}`"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')
    
    elif data == 'withdraw':
        s, u = get_bal(uid)
        msg = f"📤 **إجراءات سحب الأرباح:**\n\nرصيدك المتاح حالياً:\n🇸🇦: `{s}` ريال\n🇺🇸: `{u}` دولار\n\n💡 ملاحظة: الرسوم (20%) لفتح بوابة التحويل الدولي."
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main')]]), parse_mode='Markdown')

    elif data in ['c_sr', 'c_us']:
        curr = 'sr' if data == 'c_sr' else 'us'
        # قائمة الأسعار كما في الكود السابق
        prices = ["1000", "2000", "5000", "10000", "20000", "50000"] if curr == 'sr' else ["100", "500", "1000", "2000", "5000"]
        btns = [[InlineKeyboardButton(f"{p} {('﷼' if curr=='sr' else '$')}", callback_data=f"{curr[0]}_{p}") for p in prices[i:i+2]] for i in range(0, len(prices), 2)]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data='main')])
        await q.edit_message_text("🏦 **يرجى اختيار مبلغ الاستثمار:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith(('s_', 'u_')):
        amt = data.split('_')[1]
        addr = "سيتم تزويدك بالحساب عند الإرسال" # يمكنك وضع الحسابات هنا
        await q.edit_message_text(f"✅ تم اختيار مبلغ: **{amt}**\n\nيرجى التحويل ثم إرسال صورة الإيصال هنا ليتم تفعيل استثمارك.", parse_mode='Markdown')

    # --- 🛠️ أزرار المالك (ثابتة للإيداع المتكرر) ---
    elif data.startswith('ok_'):
        if uid not in ADMINS: return
        _, cur, val, tid = data.split('_')
        update_bal(tid, cur, val)
        
        await q.answer(f"✅ تم إضافة {val} للمشترك", show_alert=False)
        
        try:
            await context.bot.send_message(int(tid), f"🎉 **أبشر.. تم إيداع مبلغ `{val}` {('ريال' if cur=='sr' else 'دولار')} في محفظتك بنجاح!**", parse_mode='Markdown')
        except: pass

# --- 📸 معالج الصور وأزرار المالك ---
async def handle_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.photo:
        await update.message.reply_text("✅ **استلمنا الإيصال، جاري المراجعة من قبل الإدارة...**", parse_mode='Markdown')
        
        def b(v, c): return InlineKeyboardButton(f"➕ {v} {('ر' if c=='sr' else '$')}", callback_data=f"ok_{c}_{v}_{user.id}")
        
        kb = [
            [b("1000", "sr"), b("2000", "sr"), b("5000", "sr")],
            [b("10000", "sr"), b("20000", "sr"), b("50000", "sr")],
            [b("100", "us"), b("500", "us"), b("1000", "us")],
            [b("2000", "us"), b("5000", "us"), b("10000", "us")],
            [InlineKeyboardButton("❌ إغلاق / رفض", callback_data='delete_msg')]
        ]
        
        for adm in ADMINS:
            await context.bot.send_photo(adm, update.message.photo[-1].file_id, 
                                       caption=f"🔔 **إشعار إيداع جديد:**\nالاسم: {user.first_name}\nID: `{user.id}`\n\n(الأزرار ثابتة لتتمكن من إضافة مبالغ متعددة)", 
                                       reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id in ADMINS:
        await update.callback_query.message.delete()

if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(btn, pattern='^(?!delete_msg).*'))
    app.add_handler(CallbackQueryHandler(delete_msg, pattern='^delete_msg$'))
    app.add_handler(MessageHandler(filters.PHOTO, handle_img))
    
    print("🚀 البوت يعمل الآن بالتنسيق الاحترافي...")
    app.run_polling(drop_pending_updates=True)
