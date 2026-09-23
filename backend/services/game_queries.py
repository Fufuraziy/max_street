"""Общие запросы сборов (используются сервисами игр и эскроу без циклических импортов)."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.errors import NotFoundError
from models import Game


def full_game_query() -> Select[tuple[Game]]:
    """Сбор со всеми связями, нужными API и боту (участники, площадка, слот аренды)."""
    return (
        select(Game)
        .options(selectinload(Game.participants), selectinload(Game.court), selectinload(Game.slot))
        .execution_options(populate_existing=True)
    )


async def get_game(session: AsyncSession, game_id: int) -> Game:
    game = await session.scalar(full_game_query().where(Game.id == game_id))
    if game is None:
        raise NotFoundError("Сбор не найден")
    return game


async def lock_game(session: AsyncSession, game_id: int) -> Game:
    """SELECT … FOR UPDATE: операции над одним лобби (вступление, оплата, выход) идут по очереди."""
    game = await session.scalar(select(Game).where(Game.id == game_id).with_for_update())
    if game is None:
        raise NotFoundError("Сбор не найден")
    return game
