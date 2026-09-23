from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Identity
from models import User


async def upsert_user(session: AsyncSession, identity: Identity) -> None:
    """Создаёт пользователя или обновляет его имя (без commit — коммитит вызывающий код)."""
    stmt = insert(User).values(
        max_user_id=identity.max_user_id,
        name=identity.name[:100],
        username=identity.username,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.max_user_id],
        set_={
            "name": stmt.excluded.name,
            "username": func.coalesce(stmt.excluded.username, User.username),
        },
    )
    await session.execute(stmt)
