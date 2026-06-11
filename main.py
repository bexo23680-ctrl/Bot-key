# bot/main.py
import asyncio
import logging
import sys
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from .config import config
from .handlers.start import StartHandler
from .handlers.email import EmailHandlers
from .handlers.password import PasswordHandlers
from .handlers.admin import AdminHandlers
from .database.connection import init_db, init_redis
from .utils.logger import setup_logger

# إعداد التسجيل
logger = setup_logger(__name__)

class TelegramBot:
    """البوت الرئيسي"""
    
    def __init__(self):
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        self._register_handlers()
    
    def _register_handlers(self):
        """تسجيل جميع المعالجات"""
        
        # الأوامر الأساسية
        self.app.add_handler(CommandHandler("start", StartHandler.start))
        self.app.add_handler(CommandHandler("help", StartHandler.help))
        self.app.add_handler(CommandHandler("stats", StartHandler.stats))
        self.app.add_handler(CommandHandler("menu", StartHandler.menu))
        
        # أوامر الإيميلات
        self.app.add_handler(CommandHandler("newemail", EmailHandlers.create_email_cmd))
        self.app.add_handler(CommandHandler("inbox", EmailHandlers.check_inbox_cmd))
        self.app.add_handler(CommandHandler("myemails", EmailHandlers.list_emails_cmd))
        
        # أوامر كلمات السر
        self.app.add_handler(CommandHandler("password", PasswordHandlers.generate_cmd))
        self.app.add_handler(CommandHandler("passhistory", PasswordHandlers.history_cmd))
        
        # أوامر المشرفين
        self.app.add_handler(CommandHandler("admin", AdminHandlers.panel))
        self.app.add_handler(CommandHandler("broadcast", AdminHandlers.broadcast))
        self.app.add_handler(CommandHandler("stats", AdminHandlers.system_stats))
        
        # معالج الأزرار الرئيسي
        self.app.add_handler(CallbackQueryHandler(self._button_router))
        
        # معالج الأخطاء
        self.app.add_error_handler(self._error_handler)
    
    async def _button_router(self, update, context):
        """توجيه الأزرار للمعالج المناسب"""
        query = update.callback_query
        data = query.data
        
        # توجيه حسب نوع الزر
        if data.startswith('email_') or data == 'create_email':
            await EmailHandlers.handle_callback(update, context)
        elif data.startswith('pass_') or data.startswith('gen_'):
            await PasswordHandlers.handle_callback(update, context)
        elif data.startswith('admin_'):
            await AdminHandlers.handle_callback(update, context)
        elif data.startswith('inbox_'):
            await EmailHandlers.check_specific_inbox(update, context)
        else:
            await StartHandler.handle_callback(update, context)
    
    async def _error_handler(self, update, context):
        """معالج الأخطاء العام"""
        logger.error(f"Error: {context.error}", exc_info=True)
        
        if update and update.callback_query:
            await update.callback_query.answer(
                "❌ حدث خطأ. فريق الدعم تم إبلاغه.",
                show_alert=True
            )
    
    async def start_polling(self):
        """بدء البوت مع معالجة الإشارات"""
        logger.info("🚀 بدء تشغيل البوت...")
        
        # بدء البوت
        await self.app.initialize()
        await self.app.start()
        
        # بدء الاستماع
        await self.app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
        logger.info("✅ البوت جاهز للعمل!")
        
        # انتظار إشارات الإيقاف
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("🛑 جاري إيقاف البوت...")
            await self.app.stop()

async def main():
    """الدالة الرئيسية"""
    try:
        # تهيئة قواعد البيانات
        await init_db()
        await init_redis()
        logger.info("✅ قواعد البيانات جاهزة")
        
        # تشغيل البوت
        bot = TelegramBot()
        await bot.start_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.error(f"❌ خطأ مميت: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
