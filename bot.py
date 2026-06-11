import os
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import time
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ============ الإعدادات ============
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'ضع_التوكن_هنا')

# إعدادات Gmail - غيرها بإيميلك
GMAIL_USER = "your-email@gmail.com"        # ← غير هذا
GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"  # ← غير هذا

# ============ تخزين المستخدمين ============
user_emails = {}  # {user_id: {'email': ..., 'password': ..., 'created': ...}}

# ============ دوال Gmail ============

def generate_temp_email(user_id):
    """توليد إيميل مؤقت من Gmail"""
    
    # تنظيف الإيميل الأساسي
    base_email = GMAIL_USER.replace('@gmail.com', '')
    
    # توليد معرف فريد
    unique_id = f"{random.randint(10000, 99999)}{int(time.time()) % 10000}"
    
    # إنشاء الإيميل المؤقت
    temp_email = f"{base_email}+user{user_id}_{unique_id}@gmail.com"
    
    # كلمة سر عشوائية
    password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=12))
    
    return {
        'email': temp_email,
        'password': password,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=24)
    }

def send_email(to_email, subject, body):
    """إرسال إيميل"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "تم الإرسال"
    except Exception as e:
        return False, str(e)

def check_inbox_for_user(user_email):
    """فحص البريد الوارد لإيميل محدد"""
    try:
        with imaplib.IMAP4_SSL('imap.gmail.com') as mail:
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            mail.select('inbox')
            
            # البحث عن رسائل موجهة لهذا الإيميل المؤقت
            _, messages = mail.search(None, f'TO "{user_email}"')
            
            message_list = []
            for num in messages[0].split():
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email_lib.message_from_bytes(email_body)
                
                # استخراج معلومات الرسالة
                subject = message.get('Subject', 'بدون عنوان')
                sender = message.get('From', 'مجهول')
                date = message.get('Date', '')
                
                # استخراج النص
                body = ""
                if message.is_multipart():
                    for part in message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = message.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # استخراج كود التحقق إذا وجد
                code = extract_verification_code(body + subject)
                
                message_list.append({
                    'id': num.decode(),
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body[:500],
                    'code': code
                })
            
            return message_list
    except Exception as e:
        return []

def extract_verification_code(text):
    """استخراج كود التحقق من النص"""
    patterns = [
        r'\b(\d{4,8})\b',           # أرقام متسلسلة
        r'code[:\s]*(\S+)',         # code: XXXXX
        r'رمز[:\s]*(\S+)',          # رمز: XXXXX
        r'verify[:\s]*(\S+)',       # verify: XXXXX
        r'otp[:\s]*(\S+)',          # OTP: XXXXX
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

# ============ معالجات البوت ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """القائمة الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("📧 إنشاء إيميل مؤقت", callback_data='create')],
        [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
        [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='password')],
        [InlineKeyboardButton("📋 إيميلاتي", callback_data='my_emails')],
        [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
    ]
    
    await update.message.reply_text(
        "🎉 *أهلاً بك في بوت الإيميلات المؤقتة*\n\n"
        "📧 إيميلات Gmail حقيقية\n"
        "📨 تستقبل رسائل فعلية\n"
        "🔐 كلمات سر قوية\n"
        "⏰ صلاحية 24 ساعة\n\n"
        "*اختر الخدمة:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'create':
        # إنشاء إيميل جديد
        email_data = generate_temp_email(user_id)
        user_emails[user_id] = email_data
        
        remaining = email_data['expires_at'] - datetime.now()
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        text = f"""
✅ *تم إنشاء إيميل مؤقت*

📨 *الإيميل:* `{email_data['email']}`
🔑 *كلمة السر:* `{email_data['password']}`
⏰ *الصلاحية:* {hours} ساعة و {minutes} دقيقة

🌐 *إيميل Gmail حقيقي*
• يستقبل رسائل من أي موقع
• تحقق من البريد عبر زر "فحص البريد"
• مثالي للتسجيلات والتحقق
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
    
    elif data == 'check':
        # فحص البريد الوارد
        if user_id not in user_emails:
            await query.edit_message_text(
                "⚠️ *لا يوجد إيميل نشط*\nأنشئ إيميلاً جديداً أولاً.",
                parse_mode='Markdown'
            )
            return
        
        await query.edit_message_text("⏳ *جاري فحص البريد...*", parse_mode='Markdown')
        
        email_data = user_emails[user_id]
        messages = check_inbox_for_user(email_data['email'])
        
        if messages:
            text = f"📨 *البريد الوارد*\n📧 `{email_data['email']}`\n📬 {len(messages)} رسالة\n\n"
            
            for i, msg in enumerate(messages[:5], 1):
                text += f"*{i}️⃣ {msg['subject'][:40]}*\n"
                text += f"   من: {msg['sender'][:25]}\n"
                if msg['code']:
                    text += f"   🔑 كود: `{msg['code']}`\n"
                text += "\n"
        else:
            text = f"""
📨 *البريد فارغ*

📧 `{email_data['email']}`
📬 لا توجد رسائل بعد

💡 أرسل رسالة تجريبية إلى هذا الإيميل لتظهر هنا
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
            [InlineKeyboardButton("⚡ ضعيفة (8)", callback_data='pass_8')],
            [InlineKeyboardButton("🛡️ متوسطة (12)", callback_data='pass_12')],
            [InlineKeyboardButton("🔒 قوية (16)", callback_data='pass_16')],
            [InlineKeyboardButton("💪 قوية جداً (20)", callback_data='pass_20')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        
        await query.edit_message_text(
            "🔐 *اختر قوة كلمة السر:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith('pass_'):
        length = int(data.split('_')[1])
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|"
        password = ''.join(random.choice(chars) for _ in range(length))
        
        # تقييم القوة
        score = 0
        if length >= 16: score += 3
        elif length >= 12: score += 2
        elif length >= 8: score += 1
        
        if any(c.isupper() for c in password): score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*()" for c in password): score += 1
        
        if score >= 6: strength = "💪 قوية جداً"
        elif score >= 4: strength = "✅ قوية"
        elif score >= 3: strength = "⚠️ متوسطة"
        else: strength = "❌ ضعيفة"
        
        text = f"""
🔐 *كلمة سر جديدة*

🔑 `{password}`
📊 *القوة:* {strength}
📏 *الطول:* {length} حرف
✅ *أحرف كبيرة وصغيرة وأرقام ورموز*
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 أخرى", callback_data=f'pass_{length}')],
            [InlineKeyboardButton("🔙 الأطوال", callback_data='password')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == 'my_emails':
        if user_id in user_emails:
            email_data = user_emails[user_id]
            remaining = email_data['expires_at'] - datetime.now()
            
            if remaining.days < 0:
                text = "⚠️ انتهت صلاحية الإيميل"
                del user_emails[user_id]
            else:
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                
                text = f"""
📋 *إيميلك النشط*

📨 `{email_data['email']}`
🔑 `{email_data['password']}`
⏰ متبقي: {hours} ساعة و {minutes} دقيقة
📅 تاريخ الإنشاء: {email_data['created_at'].strftime('%Y-%m-%d %H:%M')}
                """
        else:
            text = "⚠️ *لا يوجد إيميلات نشطة*"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == 'help':
        text = """
ℹ️ *كيف تستخدم البوت؟*

1️⃣ *أنشئ إيميل*
   اضغط "إنشاء إيميل مؤقت"
   تحصل على إيميل Gmail حقيقي

2️⃣ *استخدمه*
   سجل في أي موقع أو خدمة
   استخدم الإيميل وكلمة السر

3️⃣ *تحقق من الكود*
   اضغط "فحص البريد"
   البوت يجيب لك كود التحقق تلقائياً!

4️⃣ *كلمة السر*
   توليد كلمات سر قوية لاستخدامها

⚠️ *ملاحظات:*
• الإيميل صالح 24 ساعة
• كل الرسائل تصل لنفس صندوق Gmail
• البوت يستخرج كود التحقق تلقائياً
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == 'back':
        keyboard = [
            [InlineKeyboardButton("📧 إنشاء إيميل مؤقت", callback_data='create')],
            [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
            [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='password')],
            [InlineKeyboardButton("📋 إيميلاتي", callback_data='my_emails')],
            [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
        ]
        await query.edit_message_text(
            "🎉 *القائمة الرئيسية*\nاختر الخدمة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def main():
    print("=" * 50)
    print("🚀 تشغيل بوت الإيميلات المؤقتة...")
    print(f"📧 Gmail: {GMAIL_USER}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ البوت جاهز!")
    app.run_polling()

if __name__ == '__main__':
    main()
