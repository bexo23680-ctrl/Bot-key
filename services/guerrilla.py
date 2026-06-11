# bot/services/guerrilla.py
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from ..config import config

logger = logging.getLogger(__name__)

class GuerrillaMailService:
    """خدمة Guerrilla Mail مع تجمع اتصالات"""
    
    def __init__(self):
        self.base_url = config.GUERRILLA_API
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_email(self) -> Dict:
        """إنشاء إيميل جديد"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        try:
            params = {'f': 'get_email_address'}
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                if 'email_addr' in data:
                    email = data['email_addr']
                    session_id = data['sid_token']
                    
                    return {
                        'success': True,
                        'email': email,
                        'session_id': session_id,
                        'expires_at': datetime.utcnow() + timedelta(hours=1),
                        'service': 'guerrilla'
                    }
                
                logger.error(f"Guerrilla API error: {data}")
                return {'success': False, 'error': 'فشل إنشاء الإيميل'}
                
        except asyncio.TimeoutError:
            logger.error("Guerrilla API timeout")
            return {'success': False, 'error': 'انتهت مهلة الاتصال'}
        except Exception as e:
            logger.error(f"Guerrilla API exception: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_inbox(self, session_id: str) -> Dict:
        """فحص البريد الوارد"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        try:
            params = {
                'f': 'fetch_email',
                'sid_token': session_id
            }
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                messages = []
                if 'list' in data:
                    for msg in data['list']:
                        messages.append({
                            'id': msg.get('mail_id'),
                            'from': msg.get('mail_from', 'مجهول'),
                            'subject': msg.get('mail_subject', 'بدون عنوان'),
                            'body': msg.get('mail_body', ''),
                            'date': msg.get('mail_date', ''),
                            'read': msg.get('mail_read', 0)
                        })
                
                return {
                    'success': True,
                    'messages': messages,
                    'count': len(messages)
                }
                
        except Exception as e:
            logger.error(f"Check inbox error: {e}")
            return {'success': False, 'error': str(e), 'messages': []}
