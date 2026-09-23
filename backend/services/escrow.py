"""Безопасный сбор MAX Escrow: виртуальный счёт лобби, взносы участников, выкуп корта и возвраты.

Правила:
* деньги не переводятся организатору: каждый участник вносит долю на эскроу-счёт лобби;
* средства заморожены, пока не собрано 100% стоимости слота;
* при 100% счёт переходит в funded, провайдер арендодателя бронирует слот (paid_to_court),
  лобби получает статус booked и номер брони;
* если к дедлайну сумма не собрана (или сбор распался), всем плательщикам делается возврат.

Все движения денег пишутся в журнал escrow_transactions. Оплата тестовая (mock СБП).
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.errors import ConflictError, NotFoundError, ValidationFailedError
from core.money import ZERO, format_rub, to_money
from core.security import Identity
from core.timeutils import utcnow
from models import EscrowTransaction, Game, GameParticipant
from models.enums import EscrowTxKind, GameStatus, PaymentStatus
from services.game_queries import get_game, lock_game
from services.mock_booking_provider import BookingError, BookingReceipt, booking_provider

logger = logging.getLogger(__name__)

DEPOSIT_METHOD = "sbp_mock"
PAYOUT_METHOD = "mock_booking"
MIN_COLLECTION_WINDOW = timedelta(minutes=30)
DEADLINE_BUFFER_BEFORE_START = timedelta(minutes=15)


@dataclass(slots=True)
class RefundItem:
    user_max_id: str
    user_name: str
    amount: Decimal


@dataclass(slots=True)
class PaymentResult:
    game: Game
    transaction: EscrowTransaction
    booked: bool
    booking: BookingReceipt | None
    refunds: list[RefundItem]


def generate_escrow_id() -> str:
    return f"ESC-{secrets.randbelow(9000) + 1000}-{secrets.token_hex(2).upper()}"


def _reference(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5).upper()}"


def compute_deadline(slot_start: datetime) -> datetime:
    """Дедлайн сбора: за ESCROW_DEADLINE_MINUTES до начала, но не раньше чем через 30 минут от создания."""
    deadline = slot_start - timedelta(minutes=settings.escrow_deadline_minutes)
    deadline = max(deadline, utcnow() + MIN_COLLECTION_WINDOW)
    return min(deadline, slot_start - DEADLINE_BUFFER_BEFORE_START)


def share_amount(game: Game) -> Decimal:
    return to_money(game.total_cost / game.required_players)


def amount_due(game: Game, paid_count: int) -> Decimal:
    """Сколько должен внести очередной участник. Последний платит точный остаток, чтобы сумма сошлась до копейки."""
    remaining = to_money(game.total_cost - game.collected_amount)
    if paid_count >= game.required_players - 1:
        return remaining
    return min(share_amount(game), remaining)


def _escrow_tx(game: Game, kind: EscrowTxKind, amount: Decimal, method: str, reference: str, user: str | None) -> EscrowTransaction:
    return EscrowTransaction(
        game_id=game.id,
        escrow_account_id=game.escrow_account_id,
        user_max_id=user,
        kind=kind.value,
        amount=to_money(amount),
        method=method,
        reference=reference,
    )


async def _participants(session: AsyncSession, game_id: int, *, lock: bool = False) -> list[GameParticipant]:
    stmt = select(GameParticipant).where(GameParticipant.game_id == game_id).order_by(GameParticipant.id)
    if lock:
        stmt = stmt.with_for_update()
    return list((await session.scalars(stmt)).all())


def refund_participant(session: AsyncSession, game: Game, participant: GameParticipant) -> RefundItem | None:
    """Возврат взноса одного участника (выход из сбора до выкупа корта)."""
    if not participant.has_paid or participant.paid_amount <= 0:
        return None
    amount = to_money(participant.paid_amount)
    session.add(_escrow_tx(game, EscrowTxKind.REFUND, amount, DEPOSIT_METHOD, _reference("RFD"), participant.user_max_id))
    game.collected_amount = to_money(game.collected_amount - amount)
    participant.has_paid = False
    participant.paid_amount = ZERO
    participant.paid_at = None
    return RefundItem(participant.user_max_id, participant.user_name, amount)


async def refund_game(session: AsyncSession, game: Game, participants: list[GameParticipant] | None = None) -> list[RefundItem]:
    """Полный возврат: всем плательщикам возвращаются взносы, сбор отменяется, слот освобождается."""
    if participants is None:
        participants = await _participants(session, game.id, lock=True)
    refunds = [item for p in participants if (item := refund_participant(session, game, p)) is not None]
    game.collected_amount = ZERO
    game.payment_status = PaymentStatus.REFUNDED.value
    game.status = GameStatus.CANCELLED.value
    return refunds


async def pay_share(session: AsyncSession, game_id: int, payer: Identity, amount: Decimal | None) -> PaymentResult:
    """Взнос доли на эскроу-счёт (тестовый СБП). При 100% — автоматический выкуп корта."""
    game = await lock_game(session, game_id)
    if not game.escrow_account_id:
        raise ValidationFailedError("Это бесплатный сбор: оплата не требуется")
    if game.payment_status == PaymentStatus.PAID_TO_COURT:
        raise ConflictError("Корт уже оплачен, вносить деньги больше не нужно")
    if game.payment_status != PaymentStatus.PENDING or game.status not in (GameStatus.RECRUITING, GameStatus.CONFIRMED):
        raise ConflictError("Сбор средств по этому лобби закрыт")
    if game.payment_deadline is not None and game.payment_deadline <= utcnow():
        raise ConflictError("Срок сбора средств истёк: внесённые деньги вернутся участникам")

    participants = await _participants(session, game_id, lock=True)
    payer_row = next((p for p in participants if p.user_max_id == payer.max_user_id), None)
    if payer_row is None:
        raise NotFoundError("Сначала присоединитесь к сбору, затем внесите долю")
    if payer_row.has_paid:
        raise ConflictError("Вы уже внесли свою долю")

    due = amount_due(game, sum(1 for p in participants if p.has_paid))
    if due <= 0:
        raise ConflictError("Вся сумма уже собрана")
    if amount is not None and to_money(amount) != due:
        raise ValidationFailedError(f"Ваша доля: {format_rub(due)}")

    # Mock-платёж СБП всегда успешен: деньги «замораживаются» на эскроу-счёте лобби.
    transaction = _escrow_tx(game, EscrowTxKind.DEPOSIT, due, DEPOSIT_METHOD, _reference("SBP"), payer.max_user_id)
    session.add(transaction)
    payer_row.has_paid = True
    payer_row.paid_amount = due
    payer_row.paid_at = utcnow()
    game.collected_amount = to_money(game.collected_amount + due)

    booking: BookingReceipt | None = None
    refunds: list[RefundItem] = []
    if game.collected_amount >= game.total_cost:
        game.payment_status = PaymentStatus.FUNDED.value
        await session.flush()
        try:
            booking = await booking_provider.book_and_pay_slot(
                session,
                court_id=game.court_id,
                slot_id=game.slot_id,
                escrow_id=game.escrow_account_id,
                total_amount=game.collected_amount,
            )
        except BookingError as exc:
            logger.warning("[escrow] %s: арендодатель отказал (%s) — возврат средств", game.escrow_account_id, exc)
            refunds = await refund_game(session, game, participants)
        else:
            session.add(_escrow_tx(game, EscrowTxKind.PAYOUT, game.total_cost, PAYOUT_METHOD, booking.receipt_id, None))
            game.payment_status = PaymentStatus.PAID_TO_COURT.value
            game.status = GameStatus.BOOKED.value
            game.booking_reference = booking.booking_reference

    await session.commit()
    logger.info(
        "[escrow] %s: взнос %s от %s, собрано %s из %s",
        game.escrow_account_id,
        due,
        payer.max_user_id,
        game.collected_amount,
        game.total_cost,
    )
    return PaymentResult(
        game=await get_game(session, game_id),
        transaction=transaction,
        booked=booking is not None,
        booking=booking,
        refunds=refunds,
    )


async def expire_overdue(session: AsyncSession) -> list[tuple[int, list[RefundItem]]]:
    """Возврат средств по всем сборам, не набравшим сумму к дедлайну."""
    overdue = (
        await session.scalars(
            select(Game)
            .where(
                Game.escrow_account_id.is_not(None),
                Game.payment_status == PaymentStatus.PENDING.value,
                Game.status.in_((GameStatus.RECRUITING.value, GameStatus.CONFIRMED.value)),
                Game.payment_deadline.is_not(None),
                Game.payment_deadline <= utcnow(),
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    result = [(game.id, await refund_game(session, game)) for game in overdue]
    if result:
        await session.commit()
    return result


async def force_expire(session: AsyncSession, game_id: int) -> tuple[Game, list[RefundItem]]:
    """Mock: досрочно наступивший дедлайн (для демонстрации сценария возврата)."""
    game = await lock_game(session, game_id)
    if not game.escrow_account_id:
        raise ValidationFailedError("У бесплатного сбора нет эскроу-счёта")
    if game.payment_status != PaymentStatus.PENDING:
        raise ConflictError("Возврат возможен только пока идёт сбор средств")
    game.payment_deadline = utcnow()
    refunds = await refund_game(session, game)
    await session.commit()
    return await get_game(session, game_id), refunds


async def statement(session: AsyncSession, game_id: int) -> tuple[Game, list[EscrowTransaction], Decimal]:
    """Выписка по эскроу-счёту: сбор, транзакции и текущий баланс."""
    game = await get_game(session, game_id)
    if not game.escrow_account_id:
        raise NotFoundError("У бесплатного сбора нет эскроу-счёта")
    transactions = list(
        (
            await session.scalars(
                select(EscrowTransaction).where(EscrowTransaction.game_id == game_id).order_by(EscrowTransaction.id)
            )
        ).all()
    )
    balance = ZERO
    for tx in transactions:
        balance += tx.amount if tx.kind == EscrowTxKind.DEPOSIT else -tx.amount
    return game, transactions, to_money(balance)
