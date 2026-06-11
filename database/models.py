# bot/database/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Text, Index
from sqlalchemy.orm import relationship
from .connection import Base

class User(Base):
    """نموذج المستخدم"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default='ar')
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    total_emails_created = Column(Integer, default=0)
    total_passwords_generated = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # العلاقات
    emails = relationship("EmailSession", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_telegram', 'telegram_id'),
        Index('idx_user_active', 'last_active'),
    )

class EmailSession(Base):
    """جلسات الإيميلات"""
    __tablename__ = 'email_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    email_address = Column(String(200), index=True, nullable=False)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    service = Column(String(50), default='guerrilla')  # guerrilla, mailtm, temp
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # العلاقات
    user = relationship("User", back_populates="emails")

class EmailMessage(Base):
    """الرسائل المستلمة"""
    __tablename__ = 'email_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), index=True, nullable=False)
    mail_id = Column(String(100))
    sender = Column(String(200))
    subject = Column(String(500))
    body = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class PasswordHistory(Base):
    """سجل كلمات السر"""
    __tablename__ = 'password_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    password_hash = Column(String(500))  # مشفرة
    strength = Column(String(20))
    length = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIUsage(Base):
    """إحصائيات الاستخدام"""
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    endpoint = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    response_time = Column(Integer)  # بالمللي ثانية
    
    __table_args__ = (
        Index('idx_usage_user_time', 'user_id', 'timestamp'),
    )
