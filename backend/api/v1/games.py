from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query

from api.deps import InitIdentityDep, SessionDep, resolve_identity
from core.config import settings
from core.money import format_rub
from models.enums import ACTIVE_GAME_STATUSES, PAYMENT_STATUS_LABELS, SportType
from schemas.game import (
    EscrowRead,
    EscrowTransactionRead,
    GameCreate,
    GameWithCourt,
    JoinResponse,
    LeaveResponse,
    PayRequest,
    PayResponse,
    PlayerRequest,
)
from services import escrow
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
    """Создатель автоматически становится первым участником лобби.

    Для коммерческого корта передаётся `slot_id`: слот временно резервируется за сбором,
    стоимость лобби берётся из слота, создаётся виртуальный эскроу-счёт `ESC-XXXX-XXXX`.
    """
    creator = resolve_identity(verified, payload.creator_max_id, payload.creator_name, payload.creator_username)
    game = await game_service.create_game(
        session,
        court_id=payload.court_id,
        sport_type=payload.sport_type.value,
        start_time=payload.start_time,
        slot_id=payload.slot_id,
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

    if result.game.escrow_account_id and result.joined:
        message = f"Вы в составе! Внесите долю {format_rub(escrow.share_amount(result.game))} на эскроу-счёт"
    elif result.confirmed:
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
    """Выход из лобби. Если участник уже внёс долю, она возвращается с эскроу-счёта."""
    player = resolve_identity(verified, payload.user_max_id, payload.user_name, payload.username)
    result = await game_service.leave_game(session, game_id, player)
    background_tasks.add_task(bot_service.notify_after_leave, result, player)

    if result.cancelled:
        message = "Вы вышли, и сбор отменён: в нём никого не осталось"
    elif result.reopened:
        message = "Вы вышли из сбора, набор снова открыт"
    else:
        message = "Вы вышли из сбора"
    if result.refund:
        message += f". Взнос {format_rub(result.refund.amount)} возвращён"
    return LeaveResponse(game=GameWithCourt.model_validate(result.game), message=message)


@router.post("/{game_id}/pay", response_model=PayResponse, summary="Внести долю в эскроу (mock СБП)")
async def pay_share(
    game_id: int,
    payload: PayRequest,
    session: SessionDep,
    verified: InitIdentityDep,
    background_tasks: BackgroundTasks,
) -> PayResponse:
    """Эмуляция оплаты доли участником: сумма зачисляется на эскроу-счёт лобби, участник помечается `has_paid`.

    Когда `collected_amount >= total_cost`: `payment_status` → `funded` → mock-провайдер арендодателя
    бронирует слот (`book_and_pay_slot`) → `paid_to_court`, лобби → `booked`, слот → `is_booked`,
    бот рассылает подтверждение брони. Реальные деньги не списываются.
    """
    payer = resolve_identity(verified, payload.user_max_id, payload.user_name or "Игрок")
    result = await escrow.pay_share(session, game_id, payer, payload.amount)
    background_tasks.add_task(
        bot_service.notify_after_payment,
        game_id,
        payer,
        result.transaction.amount,
        result.transaction.reference,
        result.booked,
        result.refunds,
    )

    game = result.game
    if result.booked:
        message = f"Корт успешно забронирован! Номер брони: #{game.booking_reference}"
    elif result.refunds:
        message = "Арендодатель не подтвердил бронь: все взносы возвращены"
    else:
        message = (
            f"Доля {format_rub(result.transaction.amount)} зачислена на эскроу-счёт. "
            f"Собрано {format_rub(game.collected_amount)} из {format_rub(game.total_cost)}"
        )
    return PayResponse(
        game=GameWithCourt.model_validate(game),
        transaction=EscrowTransactionRead.model_validate(result.transaction),
        booked=result.booked,
        booking_reference=game.booking_reference,
        message=message,
    )


@router.get("/{game_id}/escrow", response_model=EscrowRead, summary="Выписка по эскроу-счёту")
async def escrow_statement(game_id: int, session: SessionDep) -> EscrowRead:
    """Все движения по виртуальному счёту сбора: взносы, выплата арендодателю, возвраты."""
    game, transactions, balance = await escrow.statement(session, game_id)
    return EscrowRead(
        game_id=game.id,
        escrow_account_id=game.escrow_account_id or "",
        payment_status=game.payment_status,
        payment_status_label=PAYMENT_STATUS_LABELS.get(game.payment_status, game.payment_status),
        total_cost=game.total_cost,
        collected_amount=game.collected_amount,
        balance=balance,
        payment_deadline=game.payment_deadline,
        booking_reference=game.booking_reference,
        provider=settings.booking_provider_name,
        transactions=[EscrowTransactionRead.model_validate(tx) for tx in transactions],
    )
