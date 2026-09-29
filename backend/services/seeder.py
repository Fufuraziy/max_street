"""Первичное наполнение БД MAX Стрит.

* Площадки из SPOTS_DATA (дворовые и коммерческие) синхронизируются в таблицу courts.
* Расписание аренды для коммерческих кортов генерируется на ближайшие дни.
* Создаётся демонстрационное лобби 5/6 участников на коммерческом корте
  (Спортивный центр «Локомотив», аренда 3000 ₽, доля 500 ₽, 5 внесли оплату,
  6-е место свободно для мгновенной проверки Safe Split жюри).
* Создаются тестовые тикеты модуля «Народный контроль» для бесплатных спотов.
* Создаются живые открытые демо-сборы на бесплатных площадках.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.errors import DomainError
from core.security import Identity
from core.timeutils import active_since, local_now, utcnow
from models import Court, CourtDefect, CourtSlot, Game, GameParticipant, User
from models.enums import ACTIVE_GAME_STATUSES, GameStatus
from services import escrow
from services import games as game_service
from services.mock_booking_provider import SLOT_MIN_LEAD
from services.users import upsert_user

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES_PATH = FIXTURES_DIR / "courts_seed.json"
SLOTS_FIXTURES_PATH = FIXTURES_DIR / "court_slots_seed.json"

SPOTS_DATA = [
    # --- БАСКЕТБОЛ / СТРИТБОЛ (Бесплатные дворовые и общественные споты) ---
    {
        "title": "Стритбол-парк на Крестовском (Сибур Арена)",
        "sport_type": "basketball",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "Футбольная аллея, 8, Санкт-Петербург",
        "latitude": 59.9723,
        "longitude": 30.2214,
        "has_lighting": True,
        "surface": "rubber",
        "description": "Популярный спот на открытом воздухе с профессиональным резиновым покрытием и стандартными кольцами.",
    },
    {
        "title": "Баскетбольная площадка в Новой Голландии",
        "sport_type": "basketball",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "наб. Адмиралтейского канала, 2, Санкт-Петербург",
        "latitude": 59.9298,
        "longitude": 30.2891,
        "has_lighting": True,
        "surface": "acrylic",
        "description": "Открытая площадка на острове Новая Голландия. Хорошее освещение и ограждение сеткой.",
    },
    {
        "title": "Дворовая площадка на Таврической",
        "sport_type": "basketball",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "Таврическая ул., 17, Санкт-Петербург",
        "latitude": 59.9458,
        "longitude": 30.3789,
        "has_lighting": False,
        "surface": "asphalt",
        "description": "Классический уличный корт с двумя кольцами в тихом дворе Центрального района.",
    },
    {
        "title": "Стритбольный спот в Севкабель Порту",
        "sport_type": "basketball",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "Кожевенная линия, 40, Санкт-Петербург",
        "latitude": 59.9242,
        "longitude": 30.2415,
        "has_lighting": True,
        "surface": "rubber",
        "description": "Видовая площадка на берегу Финского залива. Регулярные вечерние игры 3х3.",
    },

    # --- ФУТБОЛ (Бесплатные коробки и коммерческие манежи) ---
    {
        "title": "Футбольная коробка в Парке Победы",
        "sport_type": "football",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "Кузнецовская ул., 25, Санкт-Петербург",
        "latitude": 59.8665,
        "longitude": 30.3228,
        "has_lighting": True,
        "surface": "artificial_grass",
        "description": "Общедоступная огороженная коробка с искусственным газоном и мини-футбольными воротами.",
    },
    {
        "title": "Футбольный манеж «Фабрика Футбола»",
        "sport_type": "football",
        "is_commercial": True,
        "price_per_hour": 3600,
        "address": "Софийская ул., 14, Санкт-Петербург",
        "latitude": 59.8781,
        "longitude": 30.3842,
        "has_lighting": True,
        "surface": "artificial_grass",
        "description": "Крытый манеж с раздевалками, душевыми и качественным газоном 4G. Идеально для Safe Split сборов.",
    },
    {
        "title": "Спортивный центр «Локомотив» (Мини-футбол)",
        "sport_type": "football",
        "is_commercial": True,
        "price_per_hour": 3000,
        "address": "ул. Константина Заслонова, 23/4, Санкт-Петербург",
        "latitude": 59.9176,
        "longitude": 30.3491,
        "has_lighting": True,
        "surface": "parquet",
        "description": "Крытый паркетный зал с трибунами для мини-футбола и футзала.",
    },
    {
        "title": "Открытая коробка в Удельном парке",
        "sport_type": "football",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "Фермское шоссе, 21, Санкт-Петербург",
        "latitude": 60.0072,
        "longitude": 30.3155,
        "has_lighting": False,
        "surface": "rubber",
        "description": "Бесплатная дворовая площадка рядом с тренировочной базой, доступна для свободных матчей.",
    },

    # --- ПАДЕЛ-ТЕННИС (Быстрорастущий тренд, коммерческие корты) ---
    {
        "title": "Padel Pro Arena (Петроградка)",
        "sport_type": "padel",
        "is_commercial": True,
        "price_per_hour": 2800,
        "address": "Вязовая ул., 10, Санкт-Петербург",
        "latitude": 59.9715,
        "longitude": 30.2798,
        "has_lighting": True,
        "surface": "panoramic_glass_turf",
        "description": "Панорамные корты с профессиональным кварцевым песком и итальянским освещением.",
    },
    {
        "title": "Падел-клуб «Стрела»",
        "sport_type": "padel",
        "is_commercial": True,
        "price_per_hour": 2400,
        "address": "Лиговский пр., 50, Санкт-Петербург",
        "latitude": 59.9248,
        "longitude": 30.3592,
        "has_lighting": True,
        "surface": "padel_turf",
        "description": "Удобная локация в центре города. Аренда ракеток и мячей на ресепшене.",
    },
    {
        "title": "Padel Hub Приморский",
        "sport_type": "padel",
        "is_commercial": True,
        "price_per_hour": 2600,
        "address": "Приморский пр., 72, Санкт-Петербург",
        "latitude": 59.9832,
        "longitude": 30.2071,
        "has_lighting": True,
        "surface": "panoramic_glass_turf",
        "description": "Крытый центр с 4 падел-кортами рядом с парком 300-летия.",
    },

    # --- БОЛЬШОЙ ТЕННИС (Грунтовые и хардовые корты) ---
    {
        "title": "Теннисный клуб «Гулливер»",
        "sport_type": "tennis",
        "is_commercial": True,
        "price_per_hour": 2200,
        "address": "Торфяная дорога, 7, Санкт-Петербург",
        "latitude": 59.9912,
        "longitude": 30.3014,
        "has_lighting": True,
        "surface": "hard",
        "description": "Закрытые корты с покрытием Hard, комфортная зона ожидания и душевые.",
    },
    {
        "title": "Корты спортивного комплекса «Динамо»",
        "sport_type": "tennis",
        "is_commercial": True,
        "price_per_hour": 1800,
        "address": "пр. Динамо, 44, Санкт-Петербург",
        "latitude": 59.9678,
        "longitude": 30.2647,
        "has_lighting": True,
        "surface": "clay",
        "description": "Классические грунтовые корты на Крестовском острове с вековой спортивной историей.",
    },
    {
        "title": "Теннисный центр «Арсенал»",
        "sport_type": "tennis",
        "is_commercial": True,
        "price_per_hour": 2000,
        "address": "пр. Металлистов, 51, Санкт-Петербург",
        "latitude": 59.9664,
        "longitude": 30.3989,
        "has_lighting": True,
        "surface": "tera_flex",
        "description": "Крытый зал с мягким амортизирующим покрытием для тренировок и парных матчей.",
    },

    # --- ВОРКАУТ / МНОГОФУНКЦИОНАЛЬНЫЙ СПОТ ---
    {
        "title": "Воркаут и мультиспорт зона в Муринском парке",
        "sport_type": "multisport",
        "is_commercial": False,
        "price_per_hour": 0,
        "address": "пр. Луначарского, 82, Санкт-Петербург",
        "latitude": 60.0345,
        "longitude": 30.4012,
        "has_lighting": True,
        "surface": "rubber",
        "description": "Большой открытый кластер с турниками, брусьями, стритбольным кольцом и зоной разминки.",
    },
]

DEMO_DEFECTS = [
    {
        "court_title": "Стритбол-парк на Крестовском (Сибур Арена)",
        "defect_type": "broken_ring",
        "description": "Погнуто кольцо на основном щите после вечерней игры",
        "status": "reported",
        "days_ago": 1,
        "user_max_id": "demo_def_1",
    },
    {
        "court_title": "Баскетбольная площадка в Новой Голландии",
        "defect_type": "net_missing",
        "description": "Порвана сетка на кольце",
        "status": "reported",
        "days_ago": 2,
        "user_max_id": "demo_def_2",
    },
    {
        "court_title": "Дворовая площадка на Таврической",
        "defect_type": "broken_ring",
        "description": "Погнуто кольцо, мяч застревает при бросках",
        "status": "reported",
        "days_ago": 3,
        "user_max_id": "demo_def_3",
    },
    {
        "court_title": "Футбольная коробка в Парке Победы",
        "defect_type": "net_missing",
        "description": "Порвана сетка на мини-футбольных воротах",
        "status": "reported",
        "days_ago": 1,
        "user_max_id": "demo_def_4",
    },
    {
        "court_title": "Открытая коробка в Удельном парке",
        "defect_type": "surface_damage",
        "description": "Отслоение резинового покрытия в штрафной площади",
        "status": "reported",
        "days_ago": 2,
        "user_max_id": "demo_def_5",
    },
]

DEMO_FREE_GAMES = [
    {
        "court_title": "Стритбол-парк на Крестовском (Сибур Арена)",
        "sport_type": "basketball",
        "required_players": 6,
        "start": {"in_minutes": 150},
        "comment": "Стритбол 3×3 на Сибур Арене, уровень средний. Присоединяйтесь!",
        "participants": [
            {"user_max_id": "demo_free_101", "user_name": "Даниил"},
            {"user_max_id": "demo_free_102", "user_name": "Максим"},
            {"user_max_id": "demo_free_103", "user_name": "Никита"},
            {"user_max_id": "demo_free_104", "user_name": "Егор"},
        ],
    },
    {
        "court_title": "Баскетбольная площадка в Новой Голландии",
        "sport_type": "basketball",
        "required_players": 10,
        "start": {"in_minutes": 180},
        "comment": "Баскетбол 5×5 на острове Новая Голландия. Хорошая динамичная игра.",
        "participants": [
            {"user_max_id": "demo_free_111", "user_name": "Тимофей"},
            {"user_max_id": "demo_free_112", "user_name": "Марк"},
            {"user_max_id": "demo_free_113", "user_name": "Лев"},
            {"user_max_id": "demo_free_114", "user_name": "Степан"},
            {"user_max_id": "demo_free_115", "user_name": "Богдан"},
            {"user_max_id": "demo_free_116", "user_name": "Семён"},
        ],
    },
    {
        "court_title": "Стритбольный спот в Севкабель Порту",
        "sport_type": "basketball",
        "required_players": 6,
        "start": {"in_minutes": 210},
        "comment": "Стритбол на закате у Финского залива! Ищем 3 игроков для полноценной игры 3х3.",
        "participants": [
            {"user_max_id": "demo_free_121", "user_name": "Григорий"},
            {"user_max_id": "demo_free_122", "user_name": "Ян"},
            {"user_max_id": "demo_free_123", "user_name": "Артур"},
        ],
    },
    {
        "court_title": "Футбольная коробка в Парке Победы",
        "sport_type": "football",
        "required_players": 10,
        "start": {"in_minutes": 240},
        "comment": "Футбол 5×5 в коробке. Есть мяч и манишки, ищем ещё троих!",
        "participants": [
            {"user_max_id": "demo_free_201", "user_name": "Сергей"},
            {"user_max_id": "demo_free_202", "user_name": "Павел"},
            {"user_max_id": "demo_free_203", "user_name": "Александр"},
            {"user_max_id": "demo_free_204", "user_name": "Тимур"},
            {"user_max_id": "demo_free_205", "user_name": "Владимир"},
            {"user_max_id": "demo_free_206", "user_name": "Олег"},
            {"user_max_id": "demo_free_207", "user_name": "Ярослав"},
        ],
    },
    {
        "court_title": "Волейбольные площадки на Елагином острове (ЦПКиО)",
        "sport_type": "volleyball",
        "required_players": 12,
        "start": {"in_minutes": 180},
        "comment": "Классический волейбол 6х6 в парке на воздухе. Мяч Mikasa V200W, сетка натянута!",
        "participants": [
            {"user_max_id": "demo_free_401", "user_name": "Полина"},
            {"user_max_id": "demo_free_402", "user_name": "Евгений"},
            {"user_max_id": "demo_free_403", "user_name": "Анастасия"},
            {"user_max_id": "demo_free_404", "user_name": "Владислав"},
            {"user_max_id": "demo_free_405", "user_name": "Дарья"},
            {"user_max_id": "demo_free_406", "user_name": "Игорь"},
            {"user_max_id": "demo_free_407", "user_name": "Юлия"},
            {"user_max_id": "demo_free_408", "user_name": "Антон"},
        ],
    },
    {
        "court_title": "Настольный теннис в парке Сосновка",
        "sport_type": "table_tennis",
        "required_players": 4,
        "start": {"in_minutes": 150},
        "comment": "Турнир по настольному теннису в парке. Есть запасные ракетки и новые мячи.",
        "participants": [
            {"user_max_id": "demo_free_501", "user_name": "Борис"},
            {"user_max_id": "demo_free_502", "user_name": "Светлана"},
            {"user_max_id": "demo_free_503", "user_name": "Руслан"},
        ],
    },
    {
        "court_title": "Воркаут и мультиспорт зона в Муринском парке",
        "sport_type": "workout",
        "required_players": 4,
        "start": {"in_minutes": 120},
        "comment": "Совместная тренировка на турниках и брусьях, разминка и подтягивания.",
        "participants": [
            {"user_max_id": "demo_free_301", "user_name": "Константин"},
            {"user_max_id": "demo_free_302", "user_name": "Матвей"},
            {"user_max_id": "demo_free_303", "user_name": "Арсений"},
        ],
    },
]

DAILY_SLOT_TIMES = ("09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00")


def _parse_time(value: str) -> time:
    hours, minutes = (int(part) for part in value.split(":"))
    return time(hours, minutes)


def resolve_start(spec: dict[str, Any]) -> datetime:
    """Время демо-сбора относительно момента запуска (всегда гарантированно в будущем)."""
    now = local_now()
    if "in_minutes" in spec:
        start = (now + timedelta(minutes=int(spec["in_minutes"]))).replace(second=0, microsecond=0)
        start += timedelta(minutes=(30 - start.minute % 30) % 30)
        earliest = _parse_time(spec.get("earliest", "09:00"))
        latest = _parse_time(spec.get("latest", "22:00"))
        fallback = _parse_time(spec.get("fallback", "19:00"))
        if start.time() > latest or start.time() < earliest:
            target_date = now.date() if start.time() < earliest and now.hour < 8 else now.date() + timedelta(days=1)
            return datetime.combine(target_date, fallback, tzinfo=settings.tz)
        return start
    day = now.date() + timedelta(days=int(spec.get("day_offset", 0)))
    start = datetime.combine(day, _parse_time(str(spec.get("time", "19:00"))), tzinfo=settings.tz)
    return start if start > now else start + timedelta(days=1)


def _resolve_court_sports(sport: str) -> list[str]:
    if sport == "multisport":
        return ["workout", "basketball"]
    return [sport]


def _normalize_court(item: dict[str, Any]) -> dict[str, Any]:
    sport = item.get("sport_type") or "basketball"
    surface = item.get("surface") or item.get("surface_type") or "rubber"
    desc = item.get("description", "")
    is_indoor = item.get("is_indoor", False) or any(
        w in desc.lower() for w in ("крытый", "закрытые", "паркетный зал", "манеж")
    )
    is_commercial = bool(item.get("is_commercial", False))
    rating = float(item.get("rating", 4.8 if is_commercial else 4.6))
    return {
        "title": item["title"],
        "sport_types": _resolve_court_sports(sport),
        "address": item["address"],
        "latitude": float(item["latitude"]),
        "longitude": float(item["longitude"]),
        "surface_type": surface,
        "has_lighting": bool(item.get("has_lighting", False)),
        "is_indoor": is_indoor,
        "is_commercial": is_commercial,
        "rating": rating,
        "description": desc,
    }


async def _court_ids_by_title(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Court.title, Court.id))
    return {title: court_id for title, court_id in rows.all()}


async def seed_courts(session: AsyncSession, spots: list[dict[str, Any]] = SPOTS_DATA) -> int:
    """Добавляет и обновляет споты из SPOTS_DATA в БД.

    Остальные площадки не удаляем: это площадки, добавленные пользователями через POST /courts,
    и вместе с ними каскадно удалились бы их сборы, участники, эскроу-платежи и заявки о поломках.
    """
    existing_courts = {c.title: c for c in (await session.scalars(select(Court))).all()}

    created_count = 0
    for item in spots:
        norm = _normalize_court(item)
        if norm["title"] in existing_courts:
            court = existing_courts[norm["title"]]
            for k, v in norm.items():
                setattr(court, k, v)
        else:
            court = Court(**norm)
            session.add(court)
            existing_courts[norm["title"]] = court
            created_count += 1

    await session.commit()
    return created_count


def _is_prebooked(court_title: str, day: date, start: str, share: float = 0.15) -> bool:
    digest = hashlib.sha256(f"{court_title}|{day.isoformat()}|{start}".encode()).digest()
    return digest[0] / 255 < share


async def seed_slots(session: AsyncSession, spots: list[dict[str, Any]] = SPOTS_DATA) -> int:
    """Генерирует слоты расписания для коммерческих кортов на ближайшие дни."""
    court_ids = await _court_ids_by_title(session)
    commercial_spots = [s for s in spots if s.get("is_commercial")]
    today = local_now().date()
    days_count = max(5, settings.slots_seed_days)
    rows: list[dict[str, Any]] = []

    for spot in commercial_spots:
        title = spot["title"]
        court_id = court_ids.get(title)
        if court_id is None:
            continue

        base_price = Decimal(str(spot.get("price_per_hour", 3000)))

        for offset in range(days_count):
            day = today + timedelta(days=offset)
            for slot_time_str in DAILY_SLOT_TIMES:
                start_dt = datetime.combine(day, _parse_time(slot_time_str), tzinfo=settings.tz)
                end_dt = start_dt + timedelta(minutes=90)

                # Для "Спортивный центр «Локомотив»" цена строго 3000 руб.
                if title == "Спортивный центр «Локомотив» (Мини-футбол)":
                    slot_price = Decimal("3000.00")
                else:
                    if day.weekday() >= 5:
                        slot_price = (base_price * Decimal("1.15") / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 100
                    else:
                        slot_price = base_price

                # Вечерние слоты (18:00, 19:30, 21:00) всегда свободны для игр и демо
                is_booked = False if slot_time_str in ("18:00", "19:30", "21:00") else _is_prebooked(title, day, slot_time_str)

                rows.append(
                    {
                        "court_id": court_id,
                        "start_time": start_dt,
                        "end_time": end_dt,
                        "price": slot_price,
                        "is_booked": is_booked,
                    }
                )

    if not rows:
        return 0

    result = await session.execute(
        insert(CourtSlot).values(rows).on_conflict_do_nothing(constraint="uq_court_slots_court_start")
    )
    await session.commit()
    return result.rowcount or 0


def _resolve_demo_slot_date() -> date:
    """Выбирает дату для лобби: сегодня в 19:30 (если запуск днем) или завтра в 19:30."""
    now = local_now()
    if now.hour < 16 or (now.hour == 16 and now.minute <= 30):
        return now.date()
    return now.date() + timedelta(days=1)


COMMERCIAL_DEMO_SPECS = [
    {
        "court_title": "Спортивный центр «Локомотив» (Мини-футбол)",
        "sport_type": "football",
        "required_players": 6,
        "price": Decimal("3000.00"),
        "comment": "Мини-футбол 3×3 на паркете. Ждём 6-го игрока для выкупа зала!",
        "time_str": "19:30",
        "players": [
            ("demo_jury_1", "Артём", 98.0),
            ("demo_jury_2", "Михаил", 95.0),
            ("demo_jury_3", "Алексей", 100.0),
            ("demo_jury_4", "Денис", 96.0),
            ("demo_jury_5", "Илья", 97.0),
        ],
    },
    {
        "court_title": "Padel Pro Arena (Петроградка)",
        "sport_type": "padel",
        "required_players": 4,
        "price": Decimal("2800.00"),
        "comment": "Падел 2×2 для продолжающих. Остался 1 слот, корт выкупается сразу при сборе!",
        "time_str": "18:00",
        "players": [
            ("demo_padel_1", "Ольга", 99.0),
            ("demo_padel_2", "Кирилл", 96.0),
            ("demo_padel_3", "Дмитрий", 94.0),
        ],
    },
    {
        "court_title": "Футбольный манеж «Фабрика Футбола»",
        "sport_type": "football",
        "required_players": 10,
        "price": Decimal("3600.00"),
        "comment": "Футбол 5×5 на искусственном газоне 4G. Идёт сбор долей на эскроу-счёт.",
        "time_str": "21:00",
        "players": [
            ("demo_ff_1", "Роман", 98.0),
            ("demo_ff_2", "Глеб", 95.0),
            ("demo_ff_3", "Виктор", 97.0),
            ("demo_ff_4", "Андрей", 100.0),
            ("demo_ff_5", "Максим", 93.0),
            ("demo_ff_6", "Станислав", 96.0),
            ("demo_ff_7", "Фёдор", 94.0),
        ],
    },
    {
        "court_title": "Пляжный центр «Песок»",
        "sport_type": "volleyball",
        "required_players": 4,
        "price": Decimal("2200.00"),
        "comment": "Пляжный волейбол 2×2 на тёплом кварцевом песке. Ищем 4-го игрока!",
        "time_str": "19:30",
        "players": [
            ("demo_pesok_1", "Алина", 100.0),
            ("demo_pesok_2", "Вячеслав", 97.0),
            ("demo_pesok_3", "Ксения", 95.0),
        ],
    },
    {
        "court_title": "Теннисный клуб «Ладожский»",
        "sport_type": "tennis",
        "required_players": 2,
        "price": Decimal("2000.00"),
        "comment": "Большой теннис (одиночка или спарринг). Корт хард, организатор внёс свою половину 1000 ₽.",
        "time_str": "18:00",
        "players": [
            ("demo_ten_1", "Георгий", 99.0),
        ],
    },
    {
        "court_title": "Падел-клуб «Стрела»",
        "sport_type": "padel",
        "required_players": 4,
        "price": Decimal("2400.00"),
        "comment": "Падел на Лиговском. 2 места свободно, по 600 ₽ с человека.",
        "time_str": "19:30",
        "players": [
            ("demo_str_1", "Валерий", 96.0),
            ("demo_str_2", "Елена", 98.0),
        ],
    },
]


async def seed_demo_escrow_games(session: AsyncSession) -> int:
    """Создаёт демо-лобби Safe Split на коммерческих кортах."""
    court_ids = await _court_ids_by_title(session)
    target_day = _resolve_demo_slot_date()
    created_total = 0

    for spec in COMMERCIAL_DEMO_SPECS:
        court_title = spec["court_title"]
        court_id = court_ids.get(court_title)
        if court_id is None:
            continue

        has_active = await session.scalar(
            select(func.count(Game.id)).where(
                Game.court_id == court_id,
                Game.escrow_account_id.is_not(None),
                Game.status.in_(ACTIVE_GAME_STATUSES),
                Game.start_time >= active_since(),
            )
        )
        if has_active:
            continue

        wanted_time = datetime.combine(target_day, _parse_time(spec.get("time_str", "19:30")), tzinfo=settings.tz)
        candidates = (
            await session.scalars(
                select(CourtSlot)
                .where(
                    CourtSlot.court_id == court_id,
                    CourtSlot.start_time >= utcnow() + SLOT_MIN_LEAD + timedelta(hours=1),
                    CourtSlot.is_booked.is_(False),
                )
                .order_by(CourtSlot.start_time)
            )
        ).all()
        if not candidates:
            continue

        slot = min(candidates, key=lambda s: abs((s.start_time - wanted_time).total_seconds()))
        expected_price = spec["price"]
        if slot.price != expected_price:
            slot.price = expected_price
            await session.commit()

        player_data = spec["players"]
        identities = [Identity(max_user_id=p[0], name=p[1]) for p in player_data]

        try:
            game = await game_service.create_game(
                session,
                court_id=court_id,
                sport_type=spec["sport_type"],
                start_time=None,
                slot_id=slot.id,
                required_players=spec["required_players"],
                comment=spec["comment"],
                creator=identities[0],
            )
            for identity in identities[1:]:
                await game_service.join_game(session, game.id, identity)
            for identity in identities:
                await escrow.pay_share(session, game.id, identity, None)

            for idx, p in enumerate(game.participants):
                if idx < len(player_data):
                    p.reliability_score = player_data[idx][2]
            for idx, identity in enumerate(identities):
                db_u = await session.scalar(select(User).where(User.max_user_id == identity.max_user_id))
                if db_u:
                    db_u.reliability_score = player_data[idx][2]
                    db_u.games_attended = 15 + idx
            await session.commit()
            created_total += 1
            logger.info("Создан сбор Safe Split #%s на «%s»", game.id, court_title)
        except DomainError as exc:
            await session.rollback()
            logger.warning("Не удалось создать Safe Split на «%s»: %s", court_title, exc.message)

    return created_total


async def seed_demo_games(session: AsyncSession) -> int:
    """Создаёт открытые бесплатные сборы на дворовых спотах."""
    court_ids = await _court_ids_by_title(session)
    created = 0

    for spec in DEMO_FREE_GAMES:
        court_id = court_ids.get(spec["court_title"])
        participants = spec.get("participants") or []
        if court_id is None or not participants:
            continue

        has_active = await session.scalar(
            select(func.count(Game.id)).where(
                Game.court_id == court_id,
                Game.escrow_account_id.is_(None),
                Game.status.in_(ACTIVE_GAME_STATUSES),
                Game.start_time >= active_since(),
            )
        )
        if has_active:
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
            score = float(94.0 + (index * 2) % 7)
            game.participants.append(
                GameParticipant(
                    user_max_id=person["user_max_id"],
                    user_name=person["user_name"],
                    reliability_score=score,
                    joined_at=created_at + timedelta(minutes=15 * index),
                )
            )
        session.add(game)
        for index, person in enumerate(participants):
            score = float(94.0 + (index * 2) % 7)
            await upsert_user(session, Identity(max_user_id=person["user_max_id"], name=person["user_name"]))
            db_u = await session.scalar(select(User).where(User.max_user_id == person["user_max_id"]))
            if db_u:
                db_u.reliability_score = score
                db_u.games_attended = 12 + index
        created += 1

    await session.commit()
    return created


async def seed_demo_defects(session: AsyncSession) -> int:
    """Создаёт тестовые заявки о неисправностях модуля «Народный контроль» для бесплатных спотов."""
    court_ids = await _court_ids_by_title(session)
    created = 0

    for spec in DEMO_DEFECTS:
        court_id = court_ids.get(spec["court_title"])
        if court_id is None:
            continue

        # Проверяем, нет ли уже такой открытой заявки на этой площадке
        already_reported = await session.scalar(
            select(CourtDefect.id).where(
                CourtDefect.court_id == court_id,
                CourtDefect.defect_type == spec["defect_type"],
            )
        )
        if already_reported:
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
    """Точка входа автоматического заполнения БД при старте бэкенда."""
    courts = await seed_courts(session, SPOTS_DATA)
    if courts:
        logger.info("Сид: загружено площадок — %s", courts)

    slots = await seed_slots(session, SPOTS_DATA)
    if slots:
        logger.info("Сид: добавлено слотов аренды — %s (на %s дн.)", slots, max(5, settings.slots_seed_days))

    if not settings.seed_demo_data:
        return

    defects = await seed_demo_defects(session)
    escrow_games = await seed_demo_escrow_games(session)
    free_games = await seed_demo_games(session)

    logger.info(
        "Сид завершён: площадок %s, слотов %s, заявок контроля %s, сборов с эскроу %s, открытых сборов %s",
        len(SPOTS_DATA),
        slots,
        defects,
        escrow_games,
        free_games,
    )
