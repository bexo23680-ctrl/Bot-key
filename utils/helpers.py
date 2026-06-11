# bot/utils/helpers.py
import functools
import time
from datetime import datetime
from typing import Dict
import hashlib
import hmac
from ..config import config
from ..database.models import APIUsage
from ..database.connection import redis_client
import logging

logger = logging.getLogger(__name__)

def rate_limit(max_calls: int = 30):
    """محدد معدل الطلبات"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            if not config.RATE_LIMIT_ENABLED:
                return await func(update, context, *args, **kwargs)
            
            user_id = update.effective_user.id
            key = f"rate_limit:{user_id}"
            
            # التحقق من Redis
            current = await redis_client.get(key)
            if current and int(current) >= max_calls:
                await update.callback_query.answer(
                    "⚠️ تجاوزت الحد المسموح. انتظر قليلاً...",
                    show_alert=True
                )
                return
            
            # زيادة العداد
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 60)  # تجديد كل دقيقة
            await pipe.execute()
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def log_usage(endpoint: str):
    """تسجيل استخدام API"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            start_time = time.time()
            
            try:
                result = await func(update, context, *args, **kwargs)
                success = True
            except Exception as e:
                success = False
                logger.error(f"Error in {endpoint}: {e}")
                raise
            finally:
                response_time = int((time.time() - start_time) * 1000)
                
                # حفظ في قاعدة البيانات بشكل غير متزامن
                usage = APIUsage(
                    user_id=user_id,
                    endpoint=endpoint,
                    success=success,
                    response_time=response_time
                )
                await usage.save()
            
            return result
        return wrapper
    return decorator

def encrypt_password(password: str) -> str:
    """تشفير كلمة السر"""
    key = config.ENCRYPTION_KEY.encode()
    return hmac.new(key, password.encode(), hashlib.sha256).hexdigest()

def format_time_remaining(expires_at: datetime) -> str:
    """تنسيق الوقت المتبقي"""
    now = datetime.utcnow()
    if expires_at <= now:
        return "منتهي"
    
    delta = expires_at - now
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours} ساعة و {minutes} دقيقة"
    return f"{minutes} دقيقة"
