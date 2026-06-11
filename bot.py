import os
import requests
import random
import string
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============ الإعدادات ============
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود!")
    exit(1)

# ============ تخزين ============
user_sessions = {}  # {user_id: {email, session_id, expires}}

# ============ دوال Guerrilla Mail ============

def create_email():
    """إنشاء إيميل حقيقي"""
    try:
        resp = requests.get(
            'https://api.guerrillamail.com/ajax.php?f=get_email_address',
            timeout=10
        )
        data = resp.json()
        
        if 'email_addr' in data:
            return {
                'success': True,
                'email': data['email_addr'],
                'session_id': data['sid_token'],
                'expires_at': datetime.now() + timedelta(hours=1)
            }
        
        return {'success': False, 'error': 'فشل'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_inbox(session_id):
    """فحص البريد"""
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
                
                # استخراج كود التحقق
                code = extract_code(body + subject)
                
                messages.append({
                    'from': msg.get('mail_from', 'مجهول'),
                    'subject': subject,
                    'body': body[:300],
                    'code': code
                })
        
        return messages
    except:
        return []

def extract_code(text):
    """استخراج كود التحقق"""
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[:\s]*(\S+)',
        r'otp[:\s]*(\S+)',
        r'رمز[:\s]*(\S+)',
        r'verify[:\s]*(\S+)',
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
        [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='password')],
        [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
    ]
    
    await update.message.reply_text(
        "🎉 *بوت الإيميلات المؤقتة*\n\n"
        "📧 إيميلات حقيقية\n"
        "📨 تستقبل رسائل فعلية\n"
        "🔐 كلمات سر قوية\n"
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
        await query.edit_message_text("⏳ *جاري إنشاء إيميل...*", parse_mode='Markdown')
        
        result = create_email()
        
        if result['success']:
            user_sessions[user_id] = result
            
            remaining = result['expires_at'] - datetime.now()
            minutes = remaining.seconds // 60
            
            text = f"""
✅ *تم إنشاء إيميل حقيقي*

📨 `{result['email']}`
⏰ صلاحية: {minutes} دقيقة
🌐 إيميل حقيقي يستقبل رسائل!
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
            await query.edit_message_text("❌ فشل. حاول مرة أخرى.")
    
    elif data == 'check':
        if user_id not in user_sessions:
            await query.edit_message_text("⚠️ لا يوجد إيميل نشط")
            return
        
        session = user_sessions[user_id]
        messages = check_inbox(session['session_id'])
        
        if messages:
            text = f"📨 *{len(messages)} رسالة*\n📧 `{session['email']}`\n\n"
            for i, msg in enumerate(messages, 1):
                text += f"*{i}.* {msg['subject'][:30]}\n"
                if msg['code']:
                    text += f"    🔑 `{msg['code']}`\n"
                text += "\n"
        else:
            text = f"📭 *لا رسائل*\n📧 `{session['email']}`"
        
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
            [InlineKeyboardButton("⚡ 8 أحرف", callback_data='pass_8')],
            [InlineKeyboardButton("🛡️ 12 حرف", callback_data='pass_12')],
            [InlineKeyboardButton("🔒 16 حرف", callback_data='pass_16')],
            [InlineKeyboardButton("💪 20 حرف", callback_data='pass_20')]
        ]
        await query.edit_message_text(
            "🔐 *اختر الطول:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith('pass_'):
        length = int(data.split('_')[1])
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
        pwd = ''.join(random.choice(chars) for _ in range(length))
        
        text = f"🔐 *كلمة سر*\n🔑 `{pwd}`\n📏 {length} حرف"
        
        keyboard = [
            [InlineKeyboardButton("🔄 أخرى", callback_data=f'pass_{length}')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='password')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == 'help':
        text = """
ℹ️ *كيفية الاستخدام*

1️⃣ أنشئ إيميل
2️⃣ استخدمه للتسجيل
3️⃣ اضغط "فحص البريد"
4️⃣ البوت يجيب كود التحقق!

⚠️ صلاحية الإيميل ساعة
        """
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == 'back':
        keyboard = [
            [InlineKeyboardButton("📧 إنشاء إيميل مؤقت", callback_data='create')],
            [InlineKeyboardButton("📨 فحص البريد", callback_data='check')],
            [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='password')],
            [InlineKeyboardButton("ℹ️ شرح", callback_data='help')]
        ]
        await query.edit_message_text(
            "🎉 *القائمة*\nاختر:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def main():
    print("🚀 تشغيل البوت...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ جاهز!")
    app.run_polling()

if __name__ == '__main__':
    main()
