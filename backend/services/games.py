"""Бизнес-логика лобби: создание (в том числе платного с эскроу), вступление с проверкой кворума, выход.

Используется и REST API, и чат-ботом, поэтому правила одинаковы в обоих каналах.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import ConflictError, NotFoundError, TooManyRequestsError, ValidationFailedError
from core.money import ZERO, to_money
from core.security import Identity
from core.timeutils import active_since, ensure_aware, utcnow
from models import Court, CourtSlot, Game, GameParticipant, User
from models.enums import ACTIVE_GAME_STATUSES, GameStatus, PaymentStatus, sport_label
from schemas.game import GameWithCourt
from services import escrow
from services.escrow import RefundItem
from services.event_bus import event_bus
from services.game_queries import full_game_query, get_game, lock_game
from services.mock_booking_provider import SLOT_MIN_LEAD
from services.users import upsert_user

__all__ = [
    "CheckInResult",
    "JoinResult",
    "LeaveResult",
    "calculate_haversine_distance",
    "checkin_player",
    "create_game",
    "get_game",
    "join_game",
    "leave_game",
    "list_games",
    "extract_max_link",
    "latest_game_without_chat",
    "set_chat_link",
]

MAX_ACTIVE_GAMES_PER_USER = 5
MAX_GAME_HORIZON = timedelta(days=30)
START_TIME_TOLERANCE = timedelta(minutes=5)
MAX_LINK_RE = re.compile(r"https?://(?:www\.|web\.)?max\.ru/[^\s<>\"']+", re.IGNORECASE)


@dataclass(slots=True)
class JoinResult:
    game: Game
    joined: bool
    confirmed: bool


@dataclass(slots=True)
class LeaveResult:
    game: Game
    cancelled: bool
    reopened: bool
    new_creator: GameParticipant | None
    refund: RefundItem | None = None


@dataclass(slots=True)
class CheckInResult:
    game: Game
    distance_meters: int
    reliability_score: float
    message: str


async def list_games(
    session: AsyncSession,
    *,
    court_id: int | None = None,
    user_max_id: str | None = None,
    sport_type: str | None = None,
    statuses: tuple[str, ...] | None = ACTIVE_GAME_STATUSES,
    upcoming_only: bool = True,
    limit: int = 50,
) -> list[Game]:
    stmt = full_game_query()
    if court_id is not None:
        stmt = stmt.where(Game.court_id == court_id)
    if user_max_id:
        stmt = stmt.where(Game.participants.any(GameParticipant.user_max_id == user_max_id))
    if sport_type:
        stmt = stmt.where(Game.sport_type == sport_type)
    if statuses:
        stmt = stmt.where(Game.status.in_(statuses))
    if upcoming_only:
        stmt = stmt.where(Game.start_time >= active_since())
    stmt = stmt.order_by(Game.start_time, Game.id).limit(limit)
    return list((await session.scalars(stmt)).all())


async def _reserve_slot(session: AsyncSession, court: Court, slot_id: int | None) -> CourtSlot:
    """Проверяет и блокирует слот аренды под новое платное лобби."""
    if slot_id is None:
        raise ValidationFailedError("Корт платный: выберите слот аренды")
    slot = await session.scalar(select(CourtSlot).where(CourtSlot.id == slot_id).with_for_update())
    if slot is None or slot.court_id != court.id:
        raise NotFoundError("Слот не найден в расписании этой площадки")
    if slot.is_booked:
        raise ConflictError("Этот слот уже забронирован, выберите другое время")
    if slot.start_time < utcnow() + SLOT_MIN_LEAD:
        raise ValidationFailedError("Слот начинается меньше чем через час, выберите более позднее время")
    holder = await session.scalar(
        select(Game.id).where(Game.slot_id == slot.id, Game.status.in_(ACTIVE_GAME_STATUSES))
    )
    if holder:
        raise ConflictError("На этот слот уже идёт сбор, присоединитесь к нему")
    return slot


async def create_game(
    session: AsyncSession,
    *,
    court_id: int,
    sport_type: str,
    start_time: datetime | None,
    required_players: int,
    comment: str,
    creator: Identity,
    slot_id: int | None = None,
) -> Game:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Площадка не найдена")
    sport = str(sport_type)
    if sport not in court.sport_types:
        raise ValidationFailedError(
            f"На площадке «{court.title}» нет условий для вида спорта «{sport_label(sport)}»"
        )

    active_created = await session.scalar(
        select(func.count(Game.id)).where(
            Game.creator_max_id == creator.max_user_id,
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= active_since(),
        )
    )
    if (active_created or 0) >= MAX_ACTIVE_GAMES_PER_USER:
        raise TooManyRequestsError(
            f"У вас уже {MAX_ACTIVE_GAMES_PER_USER} активных сборов: дождитесь игры или выйдите из одного из них"
        )

    game = Game(
        court_id=court.id,
        creator_max_id=creator.max_user_id,
        sport_type=sport,
        required_players=required_players,
        current_players=1,
        status=GameStatus.RECRUITING.value,
        comment=comment.strip(),
        payment_status=PaymentStatus.PENDING.value,
        total_cost=ZERO,
        collected_amount=ZERO,
    )
    if court.is_commercial:
        # Платное лобби: слот временно удерживается сбором, создаётся виртуальный эскроу-счёт.
        slot = await _reserve_slot(session, court, slot_id)
        game.slot_id = slot.id
        game.start_time = slot.start_time
        game.total_cost = to_money(slot.price)
        game.escrow_account_id = escrow.generate_escrow_id()
        game.payment_deadline = escrow.compute_deadline(slot.start_time)
    else:
        if slot_id is not None:
            raise ValidationFailedError("Площадка бесплатная: слот аренды не нужен")
        if start_time is None:
            raise ValidationFailedError("Укажите время начала")
        start = ensure_aware(start_time)
        now = utcnow()
        if start < now - START_TIME_TOLERANCE:
            raise ValidationFailedError("Время начала уже прошло, выберите время в будущем")
        if start > now + MAX_GAME_HORIZON:
            raise ValidationFailedError("Сбор можно запланировать не больше чем на 30 дней вперёд")
        game.start_time = start

    # Создатель автоматически становится первым участником со своим рейтингом надёжности.
    creator_score = await session.scalar(select(User.reliability_score).where(User.max_user_id == creator.max_user_id))
    game.participants.append(
        GameParticipant(
            user_max_id=creator.max_user_id,
            user_name=creator.name,
            reliability_score=creator_score if creator_score is not None else 100.0,
        )
    )
    session.add(game)
    await upsert_user(session, creator)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Уникальный частичный индекс uq_games_active_slot: слот успели занять параллельно.
        await session.rollback()
        raise ConflictError("На этот слот уже идёт сбор, выберите другое время") from exc
    created = await get_game(session, game.id)
    try:
        await event_bus.publish(created.id, "game_created", GameWithCourt.model_validate(created).model_dump(mode="json"))
    except Exception:
        pass
    return created


async def join_game(session: AsyncSession, game_id: int, player: Identity) -> JoinResult:
    game = await lock_game(session, game_id)

    already_joined = await session.scalar(
        select(GameParticipant.id).where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_max_id == player.max_user_id,
        )
    )
    if already_joined:
        await session.rollback()
        return JoinResult(game=await get_game(session, game_id), joined=False, confirmed=False)

    if game.status not in (GameStatus.RECRUITING, GameStatus.CONFIRMED):
        raise ConflictError("Этот сбор уже закрыт")
    if game.start_time < active_since():
        raise ConflictError("Игра уже прошла")
    if game.escrow_account_id:
        if game.payment_status != PaymentStatus.PENDING:
            raise ConflictError("Сбор средств по этому лобби закрыт")
        if game.payment_deadline is not None and game.payment_deadline <= utcnow():
            raise ConflictError("Срок сбора средств истёк")
    # Проверка кворума: вступить можно, только пока current_players < required_players.
    if game.current_players >= game.required_players:
        raise ConflictError("Лобби уже заполнено, выберите другой сбор или создайте свой")

    player_score = await session.scalar(select(User.reliability_score).where(User.max_user_id == player.max_user_id))
    session.add(
        GameParticipant(
            game_id=game.id,
            user_max_id=player.max_user_id,
            user_name=player.name,
            reliability_score=player_score if player_score is not None else 100.0,
        )
    )
    game.current_players += 1
    confirmed = False
    if game.current_players == game.required_players:
        game.status = GameStatus.CONFIRMED.value
        confirmed = True

    await upsert_user(session, player)
    await session.commit()
    updated = await get_game(session, game_id)
    try:
        await event_bus.publish(game_id, "game_updated", GameWithCourt.model_validate(updated).model_dump(mode="json"))
    except Exception:
        pass
    return JoinResult(game=updated, joined=True, confirmed=confirmed)


async def leave_game(session: AsyncSession, game_id: int, player: Identity) -> LeaveResult:
    game = await lock_game(session, game_id)
    participant = await session.scalar(
        select(GameParticipant).where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_max_id == player.max_user_id,
        )
    )
    if participant is None:
        raise NotFoundError("Вы не состоите в этом сборе")
    if game.status == GameStatus.BOOKED or game.payment_status in (PaymentStatus.FUNDED, PaymentStatus.PAID_TO_COURT):
        raise ConflictError("Корт уже оплачен из эскроу, выйти из сбора нельзя")
    if game.status not in (GameStatus.RECRUITING, GameStatus.CONFIRMED):
        raise ConflictError("Этот сбор уже закрыт")

    # Взнос вышедшего участника возвращается с эскроу-счёта.
    refund = escrow.refund_participant(session, game, participant) if game.escrow_account_id else None
    await session.delete(participant)
    await session.flush()
    game.current_players = max(0, game.current_players - 1)

    cancelled = reopened = False
    new_creator: GameParticipant | None = None
    if game.current_players == 0:
        game.status = GameStatus.CANCELLED.value
        if game.escrow_account_id:
            game.payment_status = PaymentStatus.REFUNDED.value
        cancelled = True
    else:
        if game.creator_max_id == player.max_user_id:
            # Организатор ушёл — роль переходит к следующему по времени участнику.
            new_creator = await session.scalar(
                select(GameParticipant)
                .where(GameParticipant.game_id == game_id)
                .order_by(GameParticipant.id)
                .limit(1)
            )
            if new_creator is not None:
                game.creator_max_id = new_creator.user_max_id
        if game.status == GameStatus.CONFIRMED.value and game.current_players < game.required_players:
            game.status = GameStatus.RECRUITING.value
            reopened = True

    await session.commit()
    updated = await get_game(session, game_id)
    try:
        await event_bus.publish(game_id, "game_updated", GameWithCourt.model_validate(updated).model_dump(mode="json"))
    except Exception:
        pass
    return LeaveResult(
        game=updated,
        cancelled=cancelled,
        reopened=reopened,
        new_creator=new_creator,
        refund=refund,
    )


def extract_max_link(text: str) -> str | None:
    """Первая ссылка на max.ru в тексте (приглашение в групповой чат) или None."""
    match = MAX_LINK_RE.search(text or "")
    return match.group(0).rstrip(".,;:!?)") if match else None


async def set_chat_link(session: AsyncSession, game_id: int, player: Identity, chat_link: str) -> Game:
    """Организатор привязывает к сбору групповой чат MAX (ссылку-приглашение)."""
    link = extract_max_link(chat_link)
    if link is None or len(link) > 300:
        raise ValidationFailedError("Нужна ссылка-приглашение в чат MAX вида https://max.ru/…")
    game = await lock_game(session, game_id)
    if game.creator_max_id != player.max_user_id:
        raise ConflictError("Привязать чат может только организатор сбора")
    if game.status not in ACTIVE_GAME_STATUSES:
        raise ConflictError("Сбор уже завершён или отменён")
    game.chat_link = link
    await session.commit()
    updated = await get_game(session, game_id)
    try:
        await event_bus.publish(game_id, "game_updated", GameWithCourt.model_validate(updated).model_dump(mode="json"))
    except Exception:
        pass
    return updated


async def latest_game_without_chat(session: AsyncSession, creator_max_id: str) -> Game | None:
    """Ближайший активный сбор организатора, у которого ещё нет чата."""
    return await session.scalar(
        full_game_query()
        .where(
            Game.creator_max_id == creator_max_id,
            Game.chat_link.is_(None),
            Game.status.in_(ACTIVE_GAME_STATUSES),
            Game.start_time >= active_since(),
        )
        .order_by(Game.start_time)
        .limit(1)
    )


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Вычисляет расстояние между двумя координатами на Земле в метрах."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(R * c))


async def checkin_player(
    session: AsyncSession,
    game_id: int,
    user_max_id: str,
    user_lat: float,
    user_lon: float,
    max_distance_meters: int = 400,
) -> CheckInResult:
    """Подтверждает физическое присутствие игрока на корте и обновляет карму."""
    game = await lock_game(session, game_id)
    if game.status in (GameStatus.CANCELLED.value, GameStatus.FINISHED.value):
        raise ConflictError("Этот сбор отменён или завершён")

    participant = await session.scalar(
        select(GameParticipant).where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_max_id == user_max_id,
        )
    )
    if participant is None:
        raise NotFoundError("Вы не состоите в этом сборе")

    court = await session.get(Court, game.court_id)
    if court is None:
        raise NotFoundError("Площадка не найдена")

    dist = calculate_haversine_distance(user_lat, user_lon, court.latitude, court.longitude)
    if dist > max_distance_meters:
        raise ValidationFailedError(
            f"Вы слишком далеко от площадки ({dist} м, допустимо до {max_distance_meters} м). Подойдите ближе для чек-ина!"
        )

    user = await session.scalar(select(User).where(User.max_user_id == user_max_id))
    if participant.checked_in:
        current_score = user.reliability_score if user else participant.reliability_score
        return CheckInResult(
            game=game,
            distance_meters=dist,
            reliability_score=current_score,
            message="Вы уже отметились на этом сборе!",
        )

    participant.checked_in = True
    participant.checked_in_at = utcnow()

    # Повышаем рейтинг надёжности пользователя
    if user:
        user.games_attended += 1
        total = user.games_attended + user.games_missed
        new_score = round(min(100.0, max(50.0, (user.games_attended / total) * 100.0)), 1)
        user.reliability_score = new_score
        participant.reliability_score = new_score
    else:
        new_score = 100.0

    await session.commit()
    updated = await get_game(session, game_id)
    try:
        await event_bus.publish(game_id, "game_updated", GameWithCourt.model_validate(updated).model_dump(mode="json"))
    except Exception:
        pass

    return CheckInResult(
        game=updated,
        distance_meters=dist,
        reliability_score=new_score,
        message=f"Чек-ин подтверждён! Вы на площадке ({dist} м). Карма: {new_score}%",
    )
