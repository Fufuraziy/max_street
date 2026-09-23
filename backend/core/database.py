"""Асинхронный движок SQLAlchemy, фабрика сессий и инициализация схемы."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: одна сессия на запрос."""
    async with SessionLocal() as session:
        yield session


async def wait_for_db(attempts: int = 30, delay: float = 2.0) -> None:
    """Ждём, пока PostgreSQL начнёт принимать подключения (страховка поверх healthcheck)."""
    for attempt in range(1, attempts + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - нужен любой сбой подключения
            logger.warning("База данных недоступна (попытка %s/%s): %s", attempt, attempts, exc)
            await asyncio.sleep(delay)
    raise RuntimeError("Не удалось подключиться к базе данных")


async def create_tables() -> None:
    import models  # noqa: F401 - регистрируем модели в metadata
    from core.migrations import upgrade_schema

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await upgrade_schema(engine)
