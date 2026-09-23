"""Первичное наполнение БД.

* 20 площадок Санкт-Петербурга из fixtures/courts_seed.json загружаются, если таблица courts пуста.
* Демо-сборы (SEED_DEMO_DATA=true) создаются, если в базе нет ни одного активного сбора.
  Время демо-сборов считается от момента запуска, поэтому у жюри всегда есть «живые» лобби.
* Демо-заявки о поломках создаются, если таблица court_defects пуста.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import Identity
from core.timeutils import active_since, local_now, utcnow
from models import Court, CourtDefect, Game, GameParticipant
from models.enums import ACTIVE_GAME_STATUSES, GameStatus
from services.users import upsert_user

logger = logging.getLogger(__name__)

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "courts_seed.json"
COURT_FIELDS = (
    "title",
    "sport_types",
    "address",
    "latitude",
    "longitude",
    "surface_type",
    "has_lighting",
    "is_indoor",
    "rating",
    "description",
)


def load_fixtures(path: Path = FIXTURES_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _parse_time(value: str) -> time:
    hours, minutes = (int(part) for part in value.split(":"))
    return time(hours, minutes)


def resolve_start(spec: dict[str, Any]) -> datetime:
    """Время демо-сбора относительно момента запуска.

    {"in_minutes": 120} — через N минут с округлением вверх до :00/:30. Если это ночь
    (позже "latest" или раньше "earliest"), сбор переносится на "fallback" следующего дня.
    {"day_offset": 1, "time": "19:00"} — конкретное время в указанный день.
    """
    now = local_now()
    if "in_minutes" in spec:
        start = (now + timedelta(minutes=int(spec["in_minutes"]))).replace(second=0, microsecond=0)
        start += timedelta(minutes=(30 - start.minute % 30) % 30)
        earliest = _parse_time(spec.get("earliest", "08:00"))
        latest = _parse_time(spec.get("latest", "23:00"))
        fallback = _parse_time(spec.get("fallback", "19:00"))
        if start.time() > latest:
            return datetime.combine(start.date() + timedelta(days=1), fallback, tzinfo=settings.tz)
        if start.time() < earliest:
            return datetime.combine(start.date(), fallback, tzinfo=settings.tz)
        return start
    day = now.date() + timedelta(days=int(spec.get("day_offset", 0)))
    start = datetime.combine(day, _parse_time(str(spec.get("time", "19:00"))), tzinfo=settings.tz)
    return start if start > now else start + timedelta(days=1)


async def _court_ids_by_title(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Court.title, Court.id))
    return {title: court_id for title, court_id in rows.all()}


async def seed_courts(session: AsyncSession, data: dict[str, Any]) -> int:
    if await session.scalar(select(func.count(Court.id))):
        return 0
    courts = [Court(**{key: item[key] for key in COURT_FIELDS if key in item}) for item in data.get("courts", [])]
    session.add_all(courts)
    await session.commit()
    return len(courts)


async def seed_demo_games(session: AsyncSession, data: dict[str, Any]) -> int:
    has_active = await session.scalar(
        select(func.count(Game.id)).where(
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= active_since(),
        )
    )
    if has_active:
        return 0

    court_ids = await _court_ids_by_title(session)
    created = 0
    for spec in data.get("demo_games", []):
        court_id = court_ids.get(spec["court_title"])
        participants = spec.get("participants") or []
        if court_id is None or not participants:
            logger.warning("Демо-сбор пропущен: нет площадки «%s» или участников", spec.get("court_title"))
            continue

        required = int(spec["required_players"])
        created_at = utcnow() - timedelta(minutes=15 * len(participants) + 10)
        game = Game(
            court_id=court_id,
            creator_max_id=participants[0]["user_max_id"],
            sport_type=spec["sport_type"],
            start_time=resolve_start(spec.get("start", {})),
            required_players=required,
            current_players=len(participants),
            status=GameStatus.CONFIRMED.value if len(participants) >= required else GameStatus.RECRUITING.value,
            comment=spec.get("comment", ""),
            created_at=created_at,
        )
        for index, person in enumerate(participants):
            game.participants.append(
                GameParticipant(
                    user_max_id=person["user_max_id"],
                    user_name=person["user_name"],
                    joined_at=created_at + timedelta(minutes=15 * index),
                )
            )
        session.add(game)
        for person in participants:
            await upsert_user(session, Identity(max_user_id=person["user_max_id"], name=person["user_name"]))
        created += 1

    await session.commit()
    return created


async def seed_demo_defects(session: AsyncSession, data: dict[str, Any]) -> int:
    if await session.scalar(select(func.count(CourtDefect.id))):
        return 0
    court_ids = await _court_ids_by_title(session)
    created = 0
    for spec in data.get("demo_defects", []):
        court_id = court_ids.get(spec["court_title"])
        if court_id is None:
            continue
        session.add(
            CourtDefect(
                court_id=court_id,
                user_max_id=spec["user_max_id"],
                defect_type=spec["defect_type"],
                description=spec.get("description", ""),
                status=spec.get("status", "reported"),
                created_at=utcnow() - timedelta(days=int(spec.get("days_ago", 0))),
            )
        )
        created += 1
    await session.commit()
    return created


async def run_seed(session: AsyncSession) -> None:
    data = load_fixtures()
    courts = await seed_courts(session, data)
    if courts:
        logger.info("Сид: загружено площадок — %s", courts)
    if not settings.seed_demo_data:
        return
    games = await seed_demo_games(session, data)
    defects = await seed_demo_defects(session, data)
    if games or defects:
        logger.info("Сид: демо-сборов — %s, демо-заявок о поломках — %s", games, defects)
