"""Первичное наполнение БД.

* Площадки из fixtures/courts_seed.json (20 дворовых + 5 коммерческих) добавляются, если площадки
  с таким названием ещё нет, поэтому новые корты появляются и в базе от предыдущей версии.
* Расписание аренды из fixtures/court_slots_seed.json разворачивается на ближайшие SLOTS_SEED_DAYS
  дней при каждом старте (окно «скользит», уже созданные слоты не дублируются).
* Демо-сборы (SEED_DEMO_DATA=true) создаются, если нет активных сборов соответствующего типа.
  Время считается от момента запуска, поэтому у жюри всегда есть «живые» лобби, в том числе
  платные с эскроу. Платные демо-сборы проходят через те же сервисы, что и API.
* Демо-заявки о поломках создаются, если таблица court_defects пуста.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.errors import DomainError
from core.security import Identity
from core.timeutils import active_since, local_now, utcnow
from models import Court, CourtDefect, CourtSlot, Game, GameParticipant
from models.enums import ACTIVE_GAME_STATUSES, GameStatus
from services import escrow
from services import games as game_service
from services.mock_booking_provider import SLOT_MIN_LEAD
from services.users import upsert_user

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES_PATH = FIXTURES_DIR / "courts_seed.json"
SLOTS_FIXTURES_PATH = FIXTURES_DIR / "court_slots_seed.json"
COURT_FIELDS = (
    "title",
    "sport_types",
    "address",
    "latitude",
    "longitude",
    "surface_type",
    "has_lighting",
    "is_indoor",
    "is_commercial",
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
    existing = set((await session.scalars(select(Court.title))).all())
    courts = [
        Court(**{key: item[key] for key in COURT_FIELDS if key in item})
        for item in data.get("courts", [])
        if item["title"] not in existing
    ]
    if courts:
        session.add_all(courts)
        await session.commit()
    return len(courts)


def _slot_price(base: Decimal, day: date, weekend_multiplier: Decimal) -> Decimal:
    if day.weekday() < 5:
        return base
    # Выходные дороже; округляем до 100 ₽, как в прайсах арендодателей.
    return (base * weekend_multiplier / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 100


def _is_prebooked(court_title: str, day: date, start: str, share: float) -> bool:
    """Детерминированно «занятые» у арендодателя слоты: расписание выглядит живым и стабильно между запусками."""
    digest = hashlib.sha256(f"{court_title}|{day.isoformat()}|{start}".encode()).digest()
    return digest[0] / 255 < share


async def seed_slots(session: AsyncSession, data: dict[str, Any]) -> int:
    """Разворачивает шаблон расписания на ближайшие дни (идемпотентно: ON CONFLICT DO NOTHING)."""
    court_ids = await _court_ids_by_title(session)
    weekend = Decimal(str(data.get("weekend_multiplier", 1)))
    share = float(data.get("booked_share", 0))
    today = local_now().date()
    rows: list[dict[str, Any]] = []
    for court_spec in data.get("courts", []):
        court_id = court_ids.get(court_spec["court_title"])
        if court_id is None:
            logger.warning("Расписание пропущено: нет площадки «%s»", court_spec["court_title"])
            continue
        for offset in range(max(1, settings.slots_seed_days)):
            day = today + timedelta(days=offset)
            for slot in court_spec.get("slots", []):
                start = datetime.combine(day, _parse_time(slot["start"]), tzinfo=settings.tz)
                rows.append(
                    {
                        "court_id": court_id,
                        "start_time": start,
                        "end_time": start + timedelta(minutes=int(slot.get("duration_minutes", 90))),
                        "price": _slot_price(Decimal(str(slot["price"])), day, weekend),
                        "is_booked": _is_prebooked(court_spec["court_title"], day, slot["start"], share),
                    }
                )
    if not rows:
        return 0
    result = await session.execute(
        insert(CourtSlot).values(rows).on_conflict_do_nothing(constraint="uq_court_slots_court_start")
    )
    await session.commit()
    return result.rowcount or 0


async def _pick_demo_slot(session: AsyncSession, court_id: int, spec: dict[str, Any]) -> CourtSlot | None:
    """Слот для демо-сбора: указанный в фикстуре, а если он занят — ближайший свободный вечерний."""
    day = local_now().date() + timedelta(days=int(spec.get("day_offset", 1)))
    wanted = datetime.combine(day, _parse_time(spec.get("slot_start", "19:00")), tzinfo=settings.tz)
    candidates = (
        await session.scalars(
            select(CourtSlot)
            .where(
                CourtSlot.court_id == court_id,
                CourtSlot.is_booked.is_(False),
                CourtSlot.start_time >= utcnow() + SLOT_MIN_LEAD + timedelta(hours=1),
            )
            .order_by(CourtSlot.start_time)
        )
    ).all()
    busy = set((await session.scalars(select(Game.slot_id).where(Game.slot_id.is_not(None), Game.status.in_(ACTIVE_GAME_STATUSES)))).all())
    free = [slot for slot in candidates if slot.id not in busy]
    exact = next((slot for slot in free if slot.start_time == wanted), None)
    if exact:
        return exact
    return min(free, key=lambda slot: abs((slot.start_time - wanted).total_seconds()), default=None)


async def seed_demo_escrow_games(session: AsyncSession, data: dict[str, Any]) -> int:
    """Платные демо-сборы с эскроу: создаются через сервисы (создание → вступление → взносы)."""
    has_active = await session.scalar(
        select(func.count(Game.id)).where(
            Game.escrow_account_id.is_not(None),
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= active_since(),
        )
    )
    if has_active:
        return 0
    court_ids = await _court_ids_by_title(session)
    created = 0
    for spec in data.get("demo_escrow_games", []):
        court_id = court_ids.get(spec["court_title"])
        people = spec.get("participants") or []
        slot = await _pick_demo_slot(session, court_id, spec) if court_id else None
        if court_id is None or slot is None or not people:
            logger.warning("Платный демо-сбор пропущен: «%s»", spec.get("court_title"))
            continue
        identities = [Identity(max_user_id=p["user_max_id"], name=p["user_name"]) for p in people]
        try:
            game = await game_service.create_game(
                session,
                court_id=court_id,
                sport_type=spec["sport_type"],
                start_time=None,
                slot_id=slot.id,
                required_players=int(spec["required_players"]),
                comment=spec.get("comment", ""),
                creator=identities[0],
            )
            for identity in identities[1:]:
                await game_service.join_game(session, game.id, identity)
            for person, identity in zip(people, identities, strict=True):
                if person.get("paid"):
                    await escrow.pay_share(session, game.id, identity, None)
        except DomainError as exc:
            await session.rollback()
            logger.warning("Платный демо-сбор «%s» не создан: %s", spec.get("court_title"), exc.message)
            continue
        created += 1
    return created


async def seed_demo_games(session: AsyncSession, data: dict[str, Any]) -> int:
    has_active = await session.scalar(
        select(func.count(Game.id)).where(
            Game.escrow_account_id.is_(None),
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
    slots_data = load_fixtures(SLOTS_FIXTURES_PATH)
    courts = await seed_courts(session, data)
    if courts:
        logger.info("Сид: загружено площадок — %s", courts)
    slots = await seed_slots(session, slots_data)
    if slots:
        logger.info("Сид: добавлено слотов аренды — %s (на %s дн.)", slots, settings.slots_seed_days)
    if not settings.seed_demo_data:
        return
    games = await seed_demo_games(session, data)
    escrow_games = await seed_demo_escrow_games(session, slots_data)
    defects = await seed_demo_defects(session, data)
    if games or escrow_games or defects:
        logger.info(
            "Сид: демо-сборов — %s, платных сборов с эскроу — %s, демо-заявок о поломках — %s",
            games,
            escrow_games,
            defects,
        )
