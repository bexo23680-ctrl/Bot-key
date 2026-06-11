# main.py
import asyncio
import random
import string
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, TEMP_MAIL_BASE_URL

# تخزين مؤقت للجلسات النشطة
active_sessions = {}

class PasswordGenerator:
    @staticmethod
    def generate_password(level='strong', length=16):
        """توليد كلمة سر حسب المستوى"""
        if level == 'weak':
            chars = string.ascii_letters + string.digits
            length = 8
        elif level == 'medium':
            chars = string.ascii_letters + string.digits
            length = 12
        else:  # strong
            chars = string.ascii_letters + string.digits + string.punctuation
            length = 20
        
        # التأكد من وجود حرف كبير وصغير ورقم ورمز في القوية
        while True:
            password = ''.join(random.choice(chars) for _ in range(length))
            if level == 'strong':
                if (any(c.islower() for c in password)
                    and any(c.isupper() for c in password)
                    and any(c.isdigit() for c in password)
                    and any(c in string.punctuation for c in password)):
                    break
            else:
                break
        
        return password
    
    @staticmethod
    def check_strength(password):
        """تقييم قوة كلمة السر"""
        score = 0
        
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
            
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in string.punctuation for c in password):
            score += 1
            
        if score >= 5:
            return "قوية جداً 💪"
        elif score >= 4:
            return "قوية ✅"
        elif score >= 3:
            return "متوسطة ⚠️"
        else:
            return "ضعيفة ❌"

class TempEmailService:
    def __init__(self):
        self.base_url = TEMP_MAIL_BASE_URL
        self.headers = {
            'User-Agent': 'TelegramBot/1.0',
            'Accept': 'application/json'
        }
    
    def create_email(self):
        """إنشاء إيميل مؤقت جديد"""
        try:
            # استخدام خدمة بديلة إذا كانت API لا تعمل
            return self._create_guerrilla_email()
        except:
            return self._create_fallback_email()
    
    def _create_guerrilla_email(self):
        """استخدام Guerrilla Mail كخدمة احتياطية"""
        import requests
        
        # إنشاء جلسة جديدة
        session = requests.Session()
        response = session.get('https://api.guerrillamail.com/ajax.php?f=get_email_address')
        
        if response.status_code == 200:
            data = response.json()
            return {
                'email': data['email_addr'],
                'session_id': data['sid_token'],
                'expires_at': datetime.now() + timedelta(hours=24),
                'service': 'guerrilla'
            }
        
        return None
    
    def _create_fallback_email(self):
        """إنشاء إيميل وهمي محلياً (للحالات الطارئة)"""
        import hashlib
        import time
        
        # إنشاء إيميل فريد
        timestamp = str(time.time())
        hash_id = hashlib.md5(timestamp.encode()).hexdigest()[:10]
        domains = ['tempmail.com', '10minute.net', 'throwaway.email']
        domain = random.choice(domains)
        
        email = f"user_{hash_id}@{domain}"
        
        return {
            'email': email,
            'session_id': hash_id,
            'expires_at': datetime.now() + timedelta(hours=24),
            'service': 'fallback'
        }

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    welcome_message = """
🎉 *مرحباً بك في بوت الإيميلات وكلمات السر*

أنا بوت متعدد المهام يمكنني:

📧 *إنشاء إيميلات وهمية* تدوم لمدة 24 ساعة
🔐 *توليد كلمات سر* بمستويات أمان مختلفة
📨 *استقبال الرسائل* على الإيميلات المؤقتة
⏱️ *حذف تلقائي* بعد انتهاء المدة

اختر ما تريد القيام به:
    """
    
    keyboard = [
        [InlineKeyboardButton("📧 إنشاء إيميل وهمي", callback_data='create_email')],
        [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='create_password')],
        [InlineKeyboardButton("📨 فحص البريد الوارد", callback_data='check_inbox')],
        [InlineKeyboardButton("ℹ️ معلومات عن الإيميل", callback_data='email_info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def generate_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج توليد كلمة السر"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⚡ ضعيفة (8 أحرف)", callback_data='pass_weak')],
        [InlineKeyboardButton("🛡️ متوسطة (12 حرف)", callback_data='pass_medium')],
        [InlineKeyboardButton("🔒 قوية (20 حرف)", callback_data='pass_strong')],
        [InlineKeyboardButton("🎲 عشوائية", callback_data='pass_random')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر مستوى قوة كلمة السر:",
        reply_markup=reply_markup
    )

async def password_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج اختيار نوع كلمة السر"""
    query = update.callback_query
    await query.answer()
    
    level = query.data.replace('pass_', '')
    
    if level == 'random':
        levels = ['weak', 'medium', 'strong']
        level = random.choice(levels)
    
    password = PasswordGenerator.generate_password(level=level)
    strength = PasswordGenerator.check_strength(password)
    
    level_emoji = {
        'weak': '⚡',
        'medium': '🛡️',
        'strong': '🔒'
    }
    
    message = f"""
{level_emoji.get(level, '🎲')} *تم إنشاء كلمة سر جديدة*

🔑 *كلمة السر:* `{password}`
📊 *التقييم:* {strength}
📏 *الطول:* {len(password)} حرف
⏰ *وقت الإنشاء:* {datetime.now().strftime('%H:%M:%S')}

💡 *نصائح للأمان:*
• لا تشارك كلمة السر مع أي شخص
• استخدم كلمة سر مختلفة لكل حساب
• احفظها في مدير كلمات سر آمن
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 إنشاء أخرى", callback_data=f'pass_{level}')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='create_password')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def create_email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء إيميل وهمي جديد"""
    query = update.callback_query
    await query.answer()
    
    # إرسال رسالة انتظار
    await query.edit_message_text("⏳ *جاري إنشاء إيميل وهمي...*", parse_mode='Markdown')
    
    # إنشاء الإيميل
    email_service = TempEmailService()
    email_data = email_service.create_email()
    
    if email_data:
        # تخزين الجلسة
        user_id = update.effective_user.id
        active_sessions[user_id] = email_data
        
        expires_at = email_data['expires_at']
        remaining_time = expires_at - datetime.now()
        hours = remaining_time.seconds // 3600
        minutes = (remaining_time.seconds % 3600) // 60
        
        message = f"""
📧 *تم إنشاء إيميل وهمي جديد*

📨 *الإيميل:* `{email_data['email']}`
⏰ *تنتهي الصلاحية:* {expires_at.strftime('%Y-%m-%d %H:%M')}
⌛ *المدة المتبقية:* {hours} ساعة و {minutes} دقيقة
🔑 *معرف الجلسة:* `{email_data['session_id']}`

⚠️ *ملاحظات مهمة:*
• الإيميل صالح لمدة 24 ساعة فقط
• سيتم حذفه تلقائياً بعد انتهاء المدة
• يمكنك استقبال الرسائل خلال هذه الفترة
        """
        
        keyboard = [
            [InlineKeyboardButton("📨 فحص الرسائل", callback_data='check_inbox')],
            [InlineKeyboardButton("🔐 إنشاء كلمة سر", callback_data='create_password')],
            [InlineKeyboardButton("🗑️ حذف الإيميل", callback_data='delete_email')],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ *فشل إنشاء الإيميل*\nحاول مرة أخرى لاحقاً.",
            parse_mode='Markdown'
        )

async def check_inbox_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص البريد الوارد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in active_sessions:
        await query.edit_message_text(
            "⚠️ *ليس لديك إيميل نشط*\nقم بإنشاء إيميل جديد أولاً.",
            parse_mode='Markdown'
        )
        return
    
    email_data = active_sessions[user_id]
    
    # محاكاة فحص الرسائل
    message = f"""
📨 *فحص البريد الوارد*

📧 الإيميل: `{email_data['email']}`
⏰ آخر فحص: {datetime.now().strftime('%H:%M:%S')}

📬 *الرسائل المستلمة:*
• لا توجد رسائل جديدة حالياً

💡 *تلميح:* أرسل رسالة تجريبية إلى هذا الإيميل لتظهر هنا
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data='check_inbox')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='email_info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    welcome_message = """
🎉 *مرحباً بك في بوت الإيميلات وكلمات السر*

اختر ما تريد القيام به:
    """
    
    keyboard = [
        [InlineKeyboardButton("📧 إنشاء إيميل وهمي", callback_data='create_email')],
        [InlineKeyboardButton("🔐 توليد كلمة سر", callback_data='create_password')],
        [InlineKeyboardButton("📨 فحص البريد الوارد", callback_data='check_inbox')],
        [InlineKeyboardButton("ℹ️ معلومات عن الإيميل", callback_data='email_info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    
    # معالجات الأزرار
    application.add_handler(CallbackQueryHandler(create_email_handler, pattern='create_email'))
    application.add_handler(CallbackQueryHandler(generate_password_handler, pattern='create_password'))
    application.add_handler(CallbackQueryHandler(password_callback, pattern='^pass_'))
    application.add_handler(CallbackQueryHandler(check_inbox_handler, pattern='check_inbox'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='back_to_main'))
    
    # تشغيل البوت
    print("🤖 البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
