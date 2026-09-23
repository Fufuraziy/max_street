from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from api.deps import SessionDep
from core.errors import NotFoundError, ValidationFailedError
from core.timeutils import local_now
from models import Court
from models.enums import SportType
from schemas.court import CourtCreate, CourtDetail, CourtRead
from schemas.defect import DefectRead
from schemas.game import GameRead
from schemas.slot import SlotRead
from services import courts as court_service
from services.mock_booking_provider import booking_provider

router = APIRouter(prefix="/courts", tags=["Площадки"])

SLOTS_HORIZON_DAYS = 30


def to_court_read(court: Court, active_games_today: int, price_from: Decimal | None = None) -> CourtRead:
    data = CourtRead.model_validate(court)
    data.active_games_today = active_games_today
    data.price_from = price_from
    return data


@router.get("", response_model=list[CourtRead], summary="Список площадок с фильтрами")
async def list_courts(
    session: SessionDep,
    sport_type: SportType | None = None,
    min_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    max_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    min_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    max_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    has_lighting: bool | None = None,
    is_commercial: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> list[CourtRead]:
    """Площадки в видимой области карты (bbox) с фильтром по виду спорта.

    Для каждой площадки возвращается `active_games_today` — число активных сборов на сегодня,
    для коммерческих кортов — `price_from` (минимальная цена свободного слота аренды).
    """
    items = await court_service.list_courts(
        session,
        sport_type=sport_type.value if sport_type else None,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        has_lighting=has_lighting,
        is_commercial=is_commercial,
        limit=limit,
    )
    return [to_court_read(item.court, item.active_games_today, item.price_from) for item in items]


@router.get("/{court_id}", response_model=CourtDetail, summary="Карточка площадки")
async def get_court(court_id: int, session: SessionDep) -> CourtDetail:
    """Полная информация о площадке, активные лобби и зафиксированные неисправности."""
    details = await court_service.get_court_details(session, court_id)
    base = to_court_read(details.court, details.active_games_today, details.price_from)
    return CourtDetail(
        **base.model_dump(),
        games=[GameRead.model_validate(game) for game in details.games],
        defects=[DefectRead.model_validate(defect) for defect in details.defects],
    )


@router.get("/{court_id}/slots", response_model=list[SlotRead], summary="Расписание аренды на дату")
async def list_slots(
    court_id: int,
    session: SessionDep,
    day: Annotated[date | None, Query(alias="date", description="Дата YYYY-MM-DD (по умолчанию сегодня)")] = None,
) -> list[SlotRead]:
    """Окна аренды коммерческого корта от mock-провайдера арендодателя.

    `status`: `free` — можно создать сбор; `reserved` — слот удерживает эскроу-сбор;
    `booked` — занят. Слоты, до начала которых меньше часа, не показываются.
    """
    court = await court_service.get_court(session, court_id)
    if not court.is_commercial:
        raise NotFoundError("Площадка бесплатная: расписание аренды не ведётся")
    today = local_now().date()
    day = day or today
    if day < today or day > today + timedelta(days=SLOTS_HORIZON_DAYS):
        raise ValidationFailedError(f"Дата должна быть в пределах {SLOTS_HORIZON_DAYS} дней начиная с сегодняшней")
    views = await booking_provider.get_available_slots(session, court_id, day)
    return [
        SlotRead(
            id=view.slot.id,
            court_id=view.slot.court_id,
            start_time=view.slot.start_time,
            end_time=view.slot.end_time,
            price=view.slot.price,
            duration_minutes=view.slot.duration_minutes,
            is_booked=view.slot.is_booked,
            status=view.status,
            is_available=view.is_available,
        )
        for view in views
    ]


@router.post("", response_model=CourtRead, status_code=201, summary="Добавить площадку (краудсорсинг)")
async def create_court(payload: CourtCreate, session: SessionDep) -> CourtRead:
    court = await court_service.create_court(session, payload)
    return to_court_read(court, 0)
