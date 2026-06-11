# bot/database/connection.py
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as redis
from ..config import config

# محرك قاعدة البيانات
engine = create_async_engine(
    config.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///'),
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# جلسات غير متزامنة
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Redis للتخزين المؤقت
redis_client: Optional[redis.Redis] = None

class Base(DeclarativeBase):
    pass

async def init_db():
    """تهيئة قاعدة البيانات"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    """الحصول على جلسة قاعدة بيانات"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_redis():
    """تهيئة Redis"""
    global redis_client
    redis_client = redis.from_url(
        config.REDIS_URL,
        encoding='utf-8',
        decode_responses=True
    )
    await redis_client.ping()
