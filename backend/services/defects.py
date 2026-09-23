"""Заявки о неисправностях площадок (для районных и городских служб)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.errors import ConflictError, NotFoundError
from core.security import Identity
from core.timeutils import utcnow
from models import Court, CourtDefect
from models.enums import DefectStatus
from services.users import upsert_user

DUPLICATE_WINDOW = timedelta(hours=1)


async def create_defect(
    session: AsyncSession,
    *,
    court_id: int,
    reporter: Identity,
    defect_type: str,
    description: str,
    save_user: bool,
) -> CourtDefect:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Площадка не найдена")

    duplicate_id = await session.scalar(
        select(CourtDefect.id).where(
            CourtDefect.court_id == court_id,
            CourtDefect.user_max_id == reporter.max_user_id,
            CourtDefect.defect_type == str(defect_type),
            CourtDefect.status != DefectStatus.RESOLVED.value,
            CourtDefect.created_at >= utcnow() - DUPLICATE_WINDOW,
        )
    )
    if duplicate_id:
        raise ConflictError(f"Вы уже сообщили об этой проблеме — заявка №{duplicate_id} в работе")

    defect = CourtDefect(
        court_id=court_id,
        user_max_id=reporter.max_user_id,
        defect_type=str(defect_type),
        description=description,
        status=DefectStatus.REPORTED.value,
    )
    session.add(defect)
    if save_user:
        await upsert_user(session, reporter)
    await session.commit()
    return defect


async def list_defects(
    session: AsyncSession,
    *,
    status: str | None = None,
    court_id: int | None = None,
    limit: int = 100,
) -> list[CourtDefect]:
    stmt = select(CourtDefect).options(selectinload(CourtDefect.court))
    if status:
        stmt = stmt.where(CourtDefect.status == status)
    if court_id is not None:
        stmt = stmt.where(CourtDefect.court_id == court_id)
    stmt = stmt.order_by(CourtDefect.created_at.desc()).limit(limit)
    return list((await session.scalars(stmt)).all())


async def update_defect_status(session: AsyncSession, defect_id: int, status: str) -> CourtDefect:
    defect = await session.get(CourtDefect, defect_id)
    if defect is None:
        raise NotFoundError("Заявка не найдена")
    defect.status = str(status)
    await session.commit()
    return defect
