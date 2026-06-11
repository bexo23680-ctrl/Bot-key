# bot/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """إعدادات البوت المركزية"""
    
    # توكن البوت
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    
    # قاعدة البيانات
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # خدمات الإيميلات
    GUERRILLA_API: str = 'https://api.guerrillamail.com/ajax.php'
    TEMP_MAIL_API: str = os.getenv('TEMP_MAIL_API', '')
    MAILTM_API: str = 'https://api.mail.tm'
    
    # حدود الاستخدام
    MAX_EMAILS_PER_USER: int = int(os.getenv('MAX_EMAILS_PER_USER', '5'))
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '30'))
    
    # إعدادات المشرفين
    ADMIN_IDS: list = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    
    # إعدادات التخزين المؤقت
    CACHE_TTL: int = 3600  # ساعة واحدة
    
    # إعدادات الحماية
    RATE_LIMIT_ENABLED: bool = True
    ENCRYPTION_KEY: str = os.getenv('ENCRYPTION_KEY', '')
    
    # مراقبة
    SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN', None)
    PROMETHEUS_PORT: int = int(os.getenv('PROMETHEUS_PORT', '9090'))

config = Config()
