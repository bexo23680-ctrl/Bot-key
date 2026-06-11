# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# إعدادات البوت
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# إعدادات خدمة الإيميلات المؤقتة
# سنستخدم TempMail API كمثال
TEMP_MAIL_API_KEY = os.getenv('TEMP_MAIL_API_KEY', '')
TEMP_MAIL_BASE_URL = 'https://api.tempmail.lol'
