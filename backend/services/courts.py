"""Бизнес-логика площадок: поиск, карточка, краудсорсинг, ближайшие споты."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.errors import ConflictError, NotFoundError
from core.timeutils import active_since, today_bounds
from models import Court, CourtDefect, Game
from models.enums import ACTIVE_GAME_STATUSES
from schemas.court import CourtCreate

DUPLICATE_RADIUS_M = 30.0
EARTH_RADIUS_M = 6_371_000.0


@dataclass(slots=True)
class CourtDetails:
    court: Court
    active_games_today: int
    games: list[Game]
    defects: list[CourtDefect]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    d_lat = radius_m / 111_320.0
    d_lon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    return lat - d_lat, lat + d_lat, lon - d_lon, lon + d_lon


async def active_games_today(session: AsyncSession, court_ids: list[int] | None = None) -> dict[int, int]:
    """Количество активных сборов на сегодня по площадкам."""
    day_start, day_end = today_bounds()
    since = max(day_start, active_since())
    stmt = (
        select(Game.court_id, func.count(Game.id))
        .where(
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= since,
            Game.start_time < day_end,
        )
        .group_by(Game.court_id)
    )
    if court_ids is not None:
        if not court_ids:
            return {}
        stmt = stmt.where(Game.court_id.in_(court_ids))
    rows = await session.execute(stmt)
    return {court_id: count for court_id, count in rows.all()}


async def list_courts(
    session: AsyncSession,
    *,
    sport_type: str | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    has_lighting: bool | None = None,
    limit: int = 500,
) -> list[tuple[Court, int]]:
    stmt = select(Court)
    if sport_type:
        stmt = stmt.where(Court.sport_types.contains([sport_type]))
    if min_lat is not None:
        stmt = stmt.where(Court.latitude >= min_lat)
    if max_lat is not None:
        stmt = stmt.where(Court.latitude <= max_lat)
    if min_lon is not None:
        stmt = stmt.where(Court.longitude >= min_lon)
    if max_lon is not None:
        stmt = stmt.where(Court.longitude <= max_lon)
    if has_lighting is not None:
        stmt = stmt.where(Court.has_lighting == has_lighting)
    stmt = stmt.order_by(Court.rating.desc(), Court.id).limit(limit)

    courts = list((await session.scalars(stmt)).all())
    counts = await active_games_today(session, [court.id for court in courts])
    return [(court, counts.get(court.id, 0)) for court in courts]


async def get_court(session: AsyncSession, court_id: int) -> Court:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Площадка не найдена")
    return court


async def get_court_details(session: AsyncSession, court_id: int) -> CourtDetails:
    court = await get_court(session, court_id)
    games = await session.scalars(
        select(Game)
        .options(selectinload(Game.participants))
        .where(
            Game.court_id == court_id,
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= active_since(),
        )
        .order_by(Game.start_time)
    )
    defects = await session.scalars(
        select(CourtDefect)
        .where(CourtDefect.court_id == court_id)
        .order_by(CourtDefect.created_at.desc())
        .limit(20)
    )
    counts = await active_games_today(session, [court_id])
    return CourtDetails(
        court=court,
        active_games_today=counts.get(court_id, 0),
        games=list(games.all()),
        defects=list(defects.all()),
    )


async def create_court(session: AsyncSession, data: CourtCreate) -> Court:
    min_lat, max_lat, min_lon, max_lon = _bbox(data.latitude, data.longitude, DUPLICATE_RADIUS_M * 2)
    nearby = await session.scalars(
        select(Court).where(
            Court.latitude.between(min_lat, max_lat),
            Court.longitude.between(min_lon, max_lon),
        )
    )
    for existing in nearby:
        if haversine_m(existing.latitude, existing.longitude, data.latitude, data.longitude) <= DUPLICATE_RADIUS_M:
            raise ConflictError(f"Здесь уже есть площадка «{existing.title}» — создайте сбор на ней")

    court = Court(**data.model_dump(mode="json"), rating=0.0)
    session.add(court)
    await session.commit()
    return court


async def nearest_courts(
    session: AsyncSession,
    lat: float,
    lon: float,
    *,
    limit: int = 5,
    radius_m: float = 25_000,
) -> list[tuple[Court, float, int]]:
    """Ближайшие площадки: (площадка, расстояние в метрах, сборов сегодня)."""
    min_lat, max_lat, min_lon, max_lon = _bbox(lat, lon, radius_m)
    candidates = await session.scalars(
        select(Court).where(
            Court.latitude.between(min_lat, max_lat),
            Court.longitude.between(min_lon, max_lon),
        )
    )
    ranked = sorted(
        ((court, haversine_m(lat, lon, court.latitude, court.longitude)) for court in candidates),
        key=lambda item: item[1],
    )[:limit]
    counts = await active_games_today(session, [court.id for court, _ in ranked])
    return [(court, distance, counts.get(court.id, 0)) for court, distance in ranked]
