from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query

from api.deps import InitIdentityDep, SessionDep, resolve_identity
from models.enums import ACTIVE_GAME_STATUSES, SportType
from schemas.game import GameCreate, GameWithCourt, JoinResponse, LeaveResponse, PlayerRequest
from services import games as game_service
from services.max_bot import bot_service

router = APIRouter(prefix="/games", tags=["Сборы"])


@router.get("", response_model=list[GameWithCourt], summary="Список сборов")
async def list_games(
    session: SessionDep,
    court_id: int | None = None,
    user_max_id: Annotated[str | None, Query(max_length=64, description="Сборы, где участвует пользователь")] = None,
    sport_type: SportType | None = None,
    include_past: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[GameWithCourt]:
    games = await game_service.list_games(
        session,
        court_id=court_id,
        user_max_id=user_max_id,
        sport_type=sport_type.value if sport_type else None,
        statuses=None if include_past else ACTIVE_GAME_STATUSES,
        upcoming_only=not include_past,
        limit=limit,
    )
    return [GameWithCourt.model_validate(game) for game in games]


@router.get("/{game_id}", response_model=GameWithCourt, summary="Сбор по id")
async def get_game(game_id: int, session: SessionDep) -> GameWithCourt:
    return GameWithCourt.model_validate(await game_service.get_game(session, game_id))


@router.post("", response_model=GameWithCourt, status_code=201, summary="Создать лобби")
async def create_game(payload: GameCreate, session: SessionDep, verified: InitIdentityDep) -> GameWithCourt:
    """Создатель автоматически становится первым участником лобби."""
    creator = resolve_identity(verified, payload.creator_max_id, payload.creator_name, payload.creator_username)
    game = await game_service.create_game(
        session,
        court_id=payload.court_id,
        sport_type=payload.sport_type.value,
        start_time=payload.start_time,
        required_players=payload.required_players,
        comment=payload.comment,
        creator=creator,
    )
    return GameWithCourt.model_validate(game)


@router.post("/{game_id}/join", response_model=JoinResponse, summary="Вступить в лобби (+1)")
async def join_game(
    game_id: int,
    payload: PlayerRequest,
    session: SessionDep,
    verified: InitIdentityDep,
    background_tasks: BackgroundTasks,
) -> JoinResponse:
    """Проверяет кворум. Когда набран последний игрок, статус меняется на `confirmed`,
    а сервис бота рассылает участникам уведомление в MAX."""
    player = resolve_identity(verified, payload.user_max_id, payload.user_name, payload.username)
    result = await game_service.join_game(session, game_id, player)
    if result.joined:
        background_tasks.add_task(bot_service.notify_after_join, game_id, player, result.confirmed)

    if result.confirmed:
        message = "Состав собран! Участники получат уведомление в MAX"
    elif result.joined:
        message = "Вы в составе! Бот сообщит, когда команда соберётся"
    else:
        message = "Вы уже в составе этого сбора"
    return JoinResponse(
        game=GameWithCourt.model_validate(result.game),
        joined=result.joined,
        confirmed=result.confirmed,
        message=message,
    )


@router.post("/{game_id}/leave", response_model=LeaveResponse, summary="Выйти из лобби")
async def leave_game(
    game_id: int,
    payload: PlayerRequest,
    session: SessionDep,
    verified: InitIdentityDep,
    background_tasks: BackgroundTasks,
) -> LeaveResponse:
    player = resolve_identity(verified, payload.user_max_id, payload.user_name, payload.username)
    result = await game_service.leave_game(session, game_id, player)
    background_tasks.add_task(bot_service.notify_after_leave, result, player)

    if result.cancelled:
        message = "Вы вышли, и сбор отменён: в нём никого не осталось"
    elif result.reopened:
        message = "Вы вышли из сбора, набор снова открыт"
    else:
        message = "Вы вышли из сбора"
    return LeaveResponse(game=GameWithCourt.model_validate(result.game), message=message)
