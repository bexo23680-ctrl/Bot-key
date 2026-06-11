import os
import requests
import random
import string
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود!")
    exit(1)

# نطاقات محظورة
BLOCKED_DOMAINS = [
    'guerrillamailblock.com',
    'sharklasers.com', 
    'pokemail.net',
    'guerrillamail.info',
    'guerrillamail.de'
]

user_sessions = {}

def create_email():
    """إنشاء إيميل حقيقي - يرفض النطاقات الوهمية"""
    for attempt in range(5):  # جرب 5 مرات
        try:
            # استخدام IP مباشر لتجنب النطاقات المحظورة
            resp = requests.get(
                'https://api.guerrillamail.com/ajax.php?f=get_email_address&ip=127.0.0.1&agent=Mozilla_Telegram_Bot',
                timeout=15
            )
            data = resp.json()
            
            if 'email_addr' in data:
                email = data['email_addr']
                domain = email.split('@')[1]
                
                # تحقق من النطاق
                if domain not in BLOCKED_DOMAINS:
                    return {
                        'success': True,
                        'email': email,
                        'session_id': data['sid_token'],
                        'expires_at': datetime.now() + timedelta(hours=1)
                    }
                else:
                    print(f"⚠️ نطاق مرفوض: {domain} - إعادة المحاولة...")
                    continue
        
        except Exception as e:
            print(f"محاولة {attempt+1} فشلت: {e}")
    
    return {'success': False, 'error': 'فشل بعد 5 محاولات'}

def check_inbox(session_id):
    """فحص البريد"""
    try:
        resp = requests.get(
            'https://api.guerrillamail.com/ajax.php',
            params={
                'f': 'fetch_email',
                'sid_token': session_id,
                'seq': 0
            },
            timeout=15
        )
        data = resp.json()
        
        messages = []
        if 'list' in data:
            for msg in data['list']:
                body = msg.get('mail_body', '')
                subject = msg.get('mail_subject', '')
                code = extract_code(body + subject)
                
                messages.append({
                    'from': msg.get('mail_from', 'مجهول'),
                    'subject': subject[:50],
                    'code': code,
                    'date': msg.get('mail_date', '')
                })
        
        return messages
    except Exception as e:
        print(f"خطأ: {e}")
        return []

def extract_code(text):
    """استخراج كود التحقق"""
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[:\s]*(\S+)',
        r'otp[:\s]*(\S+)',
        r'رمز[:\s]*(\S+)',
        r'verify[:\s]*(\S+)',
        r'confirmation[:\s]*(\S+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# ============ البوت ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 إنشاء إيميل مؤقت", callback_data='create')],
        [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
        [InlineKeyboardButton("🔐 كلمة سر", callback_data='password')],
        [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
    ]
    
    await update.message.reply_text(
        "🎉 *بوت الإيميلات المؤقتة*\n\n"
        "📧 إيميلات حقيقية\n"
        "📨 تستقبل رسائل\n"
        "🔐 كلمات سر\n"
        "⏰ صلاحية ساعة\n\n"
        "اختر:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'create':
        await query.edit_message_text("⏳ *جاري إنشاء إيميل حقيقي...*", parse_mode='Markdown')
        
        result = create_email()
        
        if result['success']:
            user_sessions[user_id] = result
            
            text = f"""
✅ *تم إنشاء إيميل حقيقي*

📨 `{result['email']}`
⏰ صلاحية: 60 دقيقة

🌐 *اختبره:* أرسل رسالة لهذا الإيميل
ثم اضغط "فحص البريد"
            """
            
            keyboard = [
                [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
                [InlineKeyboardButton("🔄 إيميل جديد", callback_data='create')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ *فشل إنشاء الإيميل*\nحاول مرة أخرى.",
                parse_mode='Markdown'
            )
    
    elif data == 'check':
        if user_id not in user_sessions:
            await query.edit_message_text("⚠️ لا يوجد إيميل نشط")
            return
        
        session = user_sessions[user_id]
        messages = check_inbox(session['session_id'])
        
        if messages:
            text = f"📨 *{len(messages)} رسالة*\n📧 `{session['email']}`\n\n"
            for i, msg in enumerate(messages, 1):
                text += f"*{i}.* {msg['subject']}\n"
                if msg['code']:
                    text += f"    🔑 *كود:* `{msg['code']}`\n"
                text += "\n"
        else:
            text = f"""
📭 *لا رسائل حتى الآن*

📧 `{session['email']}`

💡 *للتجربة:*
أرسل رسالة من أي إيميل إلى الإيميل أعلاه
ثم اضغط تحديث
            """
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data='check')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == 'password':
        keyboard = [
            [InlineKeyboardButton("⚡ 8", callback_data='pass_8')],
            [InlineKeyboardButton("🛡️ 12", callback_data='pass_12')],
            [InlineKeyboardButton("🔒 16", callback_data='pass_16')],
            [InlineKeyboardButton("💪 20", callback_data='pass_20')]
        ]
        await query.edit_message_text(
            "🔐 *طول كلمة السر:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith('pass_'):
        length = int(data.split('_')[1])
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd = ''.join(random.choice(chars) for _ in range(length))
        
        await query.edit_message_text(
            f"🔐 `{pwd}`\n📏 {length} حرف",
            parse_mode='Markdown'
        )
    
    elif data == 'help':
        text = """
ℹ️ *كيف تتأكد من عمل الإيميل؟*

1️⃣ أنشئ إيميل
2️⃣ افتح Gmail أو أي إيميل عندك
3️⃣ أرسل رسالة للإيميل المؤقت
4️⃣ ارجع للبوت واضغط "فحص البريد"
5️⃣ 📬 الرسالة راح تظهر!

✅ الإيميلات حقيقية وتستقبل رسائل
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == 'back':
        keyboard = [
            [InlineKeyboardButton("📧 إنشاء إيميل مؤقت", callback_data='create')],
            [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
            [InlineKeyboardButton("🔐 كلمة سر", callback_data='password')],
            [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
        ]
        await query.edit_message_text(
            "🎉 *القائمة*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def main():
    print("🚀 بدء التشغيل...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ جاهز!")
    app.run_polling()

if __name__ == '__main__':
    main()
