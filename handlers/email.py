# bot/handlers/email.py
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..services.guerrilla import GuerrillaMailService
from ..database.models import EmailSession, EmailMessage
from ..config import config
from ..utils.helpers import rate_limit, log_usage
import logging

logger = logging.getLogger(__name__)

class EmailHandlers:
    """معالجات الإيميلات"""
    
    @staticmethod
    @rate_limit(max_calls=config.MAX_REQUESTS_PER_MINUTE)
    @log_usage(endpoint='create_email')
    async def create_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء إيميل جديد"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # التحقق من حد المستخدم
        active_emails = await EmailSession.filter(
            user_id=user_id,
            is_active=True
        ).count()
        
        if active_emails >= config.MAX_EMAILS_PER_USER:
            await query.answer("⚠️ وصلت للحد الأقصى من الإيميلات النشطة", show_alert=True)
            return
        
        # رسالة انتظار
        await query.edit_message_text("⏳ *جاري إنشاء إيميل حقيقي...*", parse_mode='Markdown')
        
        # إنشاء الإيميل
        async with GuerrillaMailService() as gm:
            result = await gm.create_email()
        
        if result['success']:
            # حفظ في قاعدة البيانات
            session = EmailSession(
                user_id=user_id,
                email_address=result['email'],
                session_id=result['session_id'],
                service=result['service'],
                expires_at=result['expires_at']
            )
            await session.save()
            
            # تحديث إحصائيات المستخدم
            user = await User.get(telegram_id=user_id)
            user.total_emails_created += 1
            user.last_active = datetime.utcnow()
            await user.save()
            
            # إنشاء رسالة جميلة
            remaining = result['expires_at'] - datetime.utcnow()
            minutes = remaining.seconds // 60
            
            text = f"""
✅ *تم إنشاء إيميل حقيقي بنجاح!*

📨 *الإيميل:* `{result['email']}`
⏰ *صالح لمدة:* {minutes} دقيقة
📅 *ينتهي في:* {result['expires_at'].strftime('%H:%M:%S')}
🔑 *معرف الجلسة:* `{result['session_id'][:15]}...`

🌐 *هذا إيميل حقيقي وفعال!*
• يستقبل رسائل من أي خدمة
• مثالي للتسجيلات المؤقتة
• يمكنك فحص البريد مباشرة

📊 *إحصائياتك:*
• الإيميلات النشطة: {active_emails + 1}/{config.MAX_EMAILS_PER_USER}
• إجمالي الإيميلات: {user.total_emails_created}
            """
            
            keyboard = [
                [InlineKeyboardButton("📨 فحص البريد الآن", callback_data='check_inbox')],
                [InlineKeyboardButton("📋 إيميلاتي النشطة", callback_data='my_emails')],
                [InlineKeyboardButton("🔄 إنشاء إيميل آخر", callback_data='create_email')],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ *فشل إنشاء الإيميل*\n{result.get('error', '')}",
                parse_mode='Markdown'
            )
    
    @staticmethod
    @rate_limit(max_calls=30)
    @log_usage(endpoint='check_inbox')
    async def check_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فحص البريد الوارد مع عرض محسن"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # جلب الإيميلات النشطة
        active_emails = await EmailSession.filter(
            user_id=user_id,
            is_active=True
        ).all()
        
        if not active_emails:
            await query.edit_message_text(
                "⚠️ *لا يوجد لديك إيميلات نشطة*\nقم بإنشاء إيميل جديد أولاً.",
                parse_mode='Markdown'
            )
            return
        
        # إذا كان هناك إيميل واحد فقط، افحصه مباشرة
        if len(active_emails) == 1:
            email_session = active_emails[0]
            await EmailHandlers._show_inbox(query, email_session)
        else:
            # عرض قائمة الإيميلات للاختيار
            keyboard = []
            for email in active_emails:
                remaining = email.expires_at - datetime.utcnow()
                minutes = max(0, remaining.seconds // 60)
                keyboard.append([
                    InlineKeyboardButton(
                        f"📧 {email.email_address[:30]}... ({minutes}د)",
                        callback_data=f'inbox_{email.session_id}'
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])
            
            await query.edit_message_text(
                "📧 *اختر الإيميل لفحص بريده:*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
