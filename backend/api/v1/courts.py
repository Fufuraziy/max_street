from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from api.deps import SessionDep
from models import Court
from models.enums import SportType
from schemas.court import CourtCreate, CourtDetail, CourtRead
from schemas.defect import DefectRead
from schemas.game import GameRead
from services import courts as court_service

router = APIRouter(prefix="/courts", tags=["Площадки"])


def to_court_read(court: Court, active_games_today: int) -> CourtRead:
    data = CourtRead.model_validate(court)
    data.active_games_today = active_games_today
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
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> list[CourtRead]:
    """Площадки в видимой области карты (bbox) с фильтром по виду спорта.

    Для каждой площадки возвращается `active_games_today` — число активных сборов на сегодня.
    """
    rows = await court_service.list_courts(
        session,
        sport_type=sport_type.value if sport_type else None,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        has_lighting=has_lighting,
        limit=limit,
    )
    return [to_court_read(court, active) for court, active in rows]


@router.get("/{court_id}", response_model=CourtDetail, summary="Карточка площадки")
async def get_court(court_id: int, session: SessionDep) -> CourtDetail:
    """Полная информация о площадке, активные лобби и зафиксированные неисправности."""
    details = await court_service.get_court_details(session, court_id)
    base = to_court_read(details.court, details.active_games_today)
    return CourtDetail(
        **base.model_dump(),
        games=[GameRead.model_validate(game) for game in details.games],
        defects=[DefectRead.model_validate(defect) for defect in details.defects],
    )


@router.post("", response_model=CourtRead, status_code=201, summary="Добавить площадку (краудсорсинг)")
async def create_court(payload: CourtCreate, session: SessionDep) -> CourtRead:
    court = await court_service.create_court(session, payload)
    return to_court_read(court, 0)
