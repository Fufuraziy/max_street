"""Mock-провайдер арендодателя: расписание слотов аренды и приём брони с оплатой.

Имитирует внешнюю систему бронирования коммерческих кортов. По регламенту хакатона реальные
платёжные и бронирующие системы не подключаются: провайдер отдаёт расписание из таблицы
court_slots, а при выкупе помечает слот занятым, выдаёт номер брони и (опционально) отправляет
вебхук на BOOKING_WEBHOOK_URL. Деньги никуда не списываются.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, settings
from core.money import to_money
from core.timeutils import utcnow
from models import CourtSlot, Game
from models.enums import ACTIVE_GAME_STATUSES, SlotStatus

logger = logging.getLogger(__name__)

# Слот можно забронировать не позднее чем за час до начала.
SLOT_MIN_LEAD = timedelta(minutes=60)


class BookingError(Exception):
    """Арендодатель отказал в бронировании (слот занят, не хватает средств и т. п.)."""


@dataclass(slots=True)
class SlotView:
    slot: CourtSlot
    status: str

    @property
    def is_available(self) -> bool:
        return self.status == SlotStatus.FREE


@dataclass(slots=True)
class BookingReceipt:
    booking_reference: str
    receipt_id: str
    provider: str
    court_id: int
    slot_id: int
    amount: Decimal
    booked_at: datetime
    webhook_delivered: bool | None


class MockBookingProvider:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.name = cfg.booking_provider_name
        # Брони, «полученные» арендодателем (для демонстрации: GET /api/v1/mock/provider/bookings).
        self.received: deque[dict[str, Any]] = deque(maxlen=200)

    async def get_available_slots(self, session: AsyncSession, court_id: int, day: date) -> list[SlotView]:
        """Слоты площадки на дату (в часовом поясе города) со статусом free / reserved / booked."""
        day_start = datetime.combine(day, time.min, tzinfo=self.cfg.tz)
        day_end = day_start + timedelta(days=1)
        earliest = max(day_start, utcnow() + SLOT_MIN_LEAD)
        slots = list(
            (
                await session.scalars(
                    select(CourtSlot)
                    .where(
                        CourtSlot.court_id == court_id,
                        CourtSlot.start_time >= earliest,
                        CourtSlot.start_time < day_end,
                    )
                    .order_by(CourtSlot.start_time)
                )
            ).all()
        )
        if not slots:
            return []
        reserved = set(
            (
                await session.scalars(
                    select(Game.slot_id).where(
                        Game.slot_id.in_([slot.id for slot in slots]),
                        Game.status.in_(ACTIVE_GAME_STATUSES),
                    )
                )
            ).all()
        )
        views = []
        for slot in slots:
            if slot.is_booked:
                status = SlotStatus.BOOKED
            elif slot.id in reserved:
                status = SlotStatus.RESERVED
            else:
                status = SlotStatus.FREE
            views.append(SlotView(slot=slot, status=status.value))
        return views

    async def book_and_pay_slot(
        self,
        session: AsyncSession,
        *,
        court_id: int,
        slot_id: int,
        escrow_id: str,
        total_amount: Decimal,
    ) -> BookingReceipt:
        """Бронирует слот и «оплачивает» его из эскроу-счёта. Возвращает электронный чек с номером брони."""
        slot = await session.scalar(
            select(CourtSlot).where(CourtSlot.id == slot_id, CourtSlot.court_id == court_id).with_for_update()
        )
        if slot is None:
            raise BookingError("Слот не найден в системе арендодателя")
        if slot.is_booked:
            raise BookingError("Слот уже занят в системе арендодателя")
        if to_money(total_amount) < to_money(slot.price):
            raise BookingError("Суммы на эскроу-счёте недостаточно для оплаты слота")

        slot.is_booked = True
        receipt = BookingReceipt(
            booking_reference=f"MAX-SPORT-{secrets.randbelow(9000) + 1000}",
            receipt_id=f"RCPT-{secrets.token_hex(4).upper()}",
            provider=self.name,
            court_id=court_id,
            slot_id=slot_id,
            amount=to_money(slot.price),
            booked_at=utcnow(),
            webhook_delivered=None,
        )
        payload = {
            "event": "booking.confirmed",
            "provider": self.name,
            "booking_reference": receipt.booking_reference,
            "receipt_id": receipt.receipt_id,
            "court_id": court_id,
            "slot_id": slot_id,
            "slot_start": slot.start_time.isoformat(),
            "slot_end": slot.end_time.isoformat(),
            "amount": float(receipt.amount),
            "currency": "RUB",
            "escrow_account_id": escrow_id,
            "booked_at": receipt.booked_at.isoformat(),
        }
        receipt.webhook_delivered = await self._send_webhook(payload)
        self.received.appendleft({**payload, "webhook_delivered": receipt.webhook_delivered})
        logger.info(
            "[booking] %s: слот #%s (корт #%s) выкуплен за %s ₽, бронь %s, эскроу %s",
            self.name,
            slot_id,
            court_id,
            receipt.amount,
            receipt.booking_reference,
            escrow_id,
        )
        return receipt

    async def _send_webhook(self, payload: dict[str, Any]) -> bool | None:
        """Вебхук во внешнюю систему арендодателя (если задан BOOKING_WEBHOOK_URL), подписанный HMAC."""
        if not self.cfg.booking_webhook_url:
            return None
        body = json.dumps(payload, ensure_ascii=False).encode()
        headers = {"Content-Type": "application/json"}
        if self.cfg.booking_webhook_secret:
            signature = hmac.new(self.cfg.booking_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-MaxStreet-Signature"] = f"sha256={signature}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.cfg.booking_webhook_url, content=body, headers=headers)
            if response.status_code >= 400:
                logger.warning("Вебхук арендодателя вернул %s", response.status_code)
                return False
            return True
        except httpx.HTTPError as exc:
            logger.warning("Вебхук арендодателя недоступен: %s", exc)
            return False


booking_provider = MockBookingProvider(settings)
