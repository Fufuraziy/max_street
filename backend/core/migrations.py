"""Идемпотентное обновление схемы для баз, созданных предыдущей версией.

`Base.metadata.create_all` создаёт только отсутствующие таблицы, но не добавляет колонки в
существующие. Для MVP вместо Alembic используется список безопасных DDL с IF NOT EXISTS:
на свежей базе они ничего не меняют, на старом volume — добавляют поля аренды и эскроу.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

UPGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE courts ADD COLUMN IF NOT EXISTS is_commercial BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS slot_id BIGINT REFERENCES court_slots(id) ON DELETE SET NULL",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS escrow_account_id VARCHAR(64) UNIQUE",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS total_cost NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS collected_amount NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS payment_status VARCHAR(32) NOT NULL DEFAULT 'pending'",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS payment_deadline TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE games ADD COLUMN IF NOT EXISTS booking_reference VARCHAR(64)",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS has_paid BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS reliability_score DOUBLE PRECISION NOT NULL DEFAULT 100.0",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS checked_in BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE game_participants ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS reliability_score DOUBLE PRECISION NOT NULL DEFAULT 100.0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS games_attended INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS games_missed INTEGER NOT NULL DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS ix_games_slot_id ON games (slot_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_games_active_slot ON games (slot_id) "
    "WHERE slot_id IS NOT NULL AND status IN ('recruiting', 'confirmed', 'booked')",
)


async def upgrade_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for statement in UPGRADE_STATEMENTS:
            await conn.execute(text(statement))
    logger.debug("Схема БД актуальна (%s проверок)", len(UPGRADE_STATEMENTS))
