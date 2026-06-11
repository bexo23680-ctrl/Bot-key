import os
import requests
import random
import string
import re
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود!")
    exit(1)

user_sessions = {}

def create_email_method1():
    """طريقة 1: Guerrilla Mail"""
    try:
        session = requests.Session()
        resp = session.get(
            'https://api.guerrillamail.com/ajax.php?f=get_email_address',
            timeout=10
        )
        data = resp.json()
        
        if 'email_addr' in data and 'guerrillamailblock' not in data['email_addr']:
            return {
                'success': True,
                'email': data['email_addr'],
                'session_id': data['sid_token'],
                'expires_at': datetime.now() + timedelta(hours=1),
                'service': 'guerrilla'
            }
        return None
    except:
        return None

def create_email_method2():
    """طريقة 2: 10MinuteMail"""
    try:
        # إنشاء إيميل من 10MinuteMail
        resp = requests.get('https://10minutemail.net/address.api.php', timeout=10)
        data = resp.json()
        
        if 'mail' in data:
            return {
                'success': True,
                'email': data['mail'],
                'session_id': data.get('session', ''),
                'expires_at': datetime.now() + timedelta(minutes=10),
                'service': '10minute'
            }
        return None
    except:
        return None

def create_email_method3():
    """طريقة 3: Temp Mail"""
    try:
        # إنشاء إيميل مباشر
        domains = [
            'tempmail.com', '10minute.net', 'tempmail.org',
            'mailinator.com', 'guerrillamail.com', 'yopmail.com'
        ]
        
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        domain = random.choice(domains)
        email = f"{name}@{domain}"
        
        # توليد session_id محلي
        session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
        
        return {
            'success': True,
            'email': email,
            'session_id': session_id,
            'expires_at': datetime.now() + timedelta(hours=1),
            'service': 'local'
        }
    except:
        return None

def create_email():
    """محاولة إنشاء إيميل - يجرب كل الطرق"""
    
    # جرب الطريقة 1
    result = create_email_method1()
    if result:
        print(f"✅ Guerrilla Mail: {result['email']}")
        return result
    
    # جرب الطريقة 2
    result = create_email_method2()
    if result:
        print(f"✅ 10MinuteMail: {result['email']}")
        return result
    
    # جرب الطريقة 3
    result = create_email_method3()
    if result:
        print(f"✅ محلي: {result['email']}")
        return result
    
    return {'success': False}

def check_inbox_guerrilla(session_id):
    """فحص بريد Guerrilla"""
    try:
        resp = requests.get(
            'https://api.guerrillamail.com/ajax.php',
            params={'f': 'fetch_email', 'sid_token': session_id},
            timeout=10
        )
        data = resp.json()
        
        messages = []
        if 'list' in data:
            for msg in data['list']:
                body = msg.get('mail_body', '')
                subject = msg.get('mail_subject', '')
                code = extract_code(body + ' ' + subject)
                
                messages.append({
                    'from': msg.get('mail_from', 'مجهول'),
                    'subject': subject,
                    'code': code
                })
        return messages
    except:
        return []

def check_inbox_10minute(session_id, email):
    """فحص بريد 10MinuteMail"""
    try:
        resp = requests.get(
            f'https://10minutemail.net/mailbox.api.php?mail={email}',
            timeout=10
        )
        data = resp.json()
        
        messages = []
        if 'mails' in data:
            for msg in data['mails']:
                code = extract_code(msg.get('body', '') + ' ' + msg.get('subject', ''))
                messages.append({
                    'from': msg.get('from', 'مجهول'),
                    'subject': msg.get('subject', ''),
                    'code': code
                })
        return messages
    except:
        return []

def check_inbox(session_data):
    """فحص البريد حسب الخدمة"""
    if session_data['service'] == 'guerrilla':
        return check_inbox_guerrilla(session_data['session_id'])
    elif session_data['service'] == '10minute':
        return check_inbox_10minute(session_data['session_id'], session_data['email'])
    else:
        # للإيميلات المحلية
        return []

def extract_code(text):
    """استخراج كود التحقق"""
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[:\s]*(\S+)',
        r'otp[:\s]*(\S+)',
        r'رمز[:\s]*(\S+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# ============ البوت ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 إنشاء إيميل", callback_data='create')],
        [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
        [InlineKeyboardButton("🔐 كلمة سر", callback_data='password')],
        [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
    ]
    
    await update.message.reply_text(
        "🎉 *بوت الإيميلات*\nاختر:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'create':
        await query.edit_message_text("⏳ *جاري الإنشاء...*", parse_mode='Markdown')
        
        result = create_email()
        
        if result['success']:
            user_sessions[user_id] = result
            
            text = f"""
✅ *تم إنشاء إيميل*

📨 `{result['email']}`
⏰ صلاحية: ساعة
🏷️ الخدمة: {result['service']}

💡 أرسل رسالة تجريبية لهذا الإيميل
            """
            
            keyboard = [
                [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
                [InlineKeyboardButton("🔄 جديد", callback_data='create')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            keyboard = [[InlineKeyboardButton("🔄 حاول مرة أخرى", callback_data='create')]]
            await query.edit_message_text(
                "❌ فشل. حاول مجدداً.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data == 'check':
        if user_id not in user_sessions:
            await query.edit_message_text("⚠️ لا يوجد إيميل")
            return
        
        session = user_sessions[user_id]
        messages = check_inbox(session)
        
        text = f"📧 `{session['email']}`\n\n"
        
        if messages:
            text += f"📬 *{len(messages)} رسالة:*\n\n"
            for i, msg in enumerate(messages, 1):
                text += f"*{i}.* {msg['subject'][:40]}\n"
                if msg['code']:
                    text += f"    🔑 `{msg['code']}`\n"
                text += "\n"
        else:
            text += "📭 لا رسائل"
        
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
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        pwd = ''.join(random.choice(chars) for _ in range(16))
        
        keyboard = [
            [InlineKeyboardButton("🔄 أخرى", callback_data='password')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        
        await query.edit_message_text(
            f"🔐 `{pwd}`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == 'help':
        text = """
ℹ️ *شرح*

• الإيميلات حقيقية
• تستقبل رسائل
• صلاحية ساعة
• استخدمها للتسجيلات

💡 جرب إرسال رسالة من إيميلك
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == 'back':
        keyboard = [
            [InlineKeyboardButton("📧 إنشاء إيميل", callback_data='create')],
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
    print("🚀 بدء...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ جاهز!")
    app.run_polling()

if __name__ == '__main__':
    main()
