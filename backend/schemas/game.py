from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from core.money import ZERO, to_money
from models.enums import GAME_STATUS_LABELS, PAYMENT_STATUS_LABELS, SportType
from schemas.common import MaxUserId, Money, PersonName, Username
from schemas.slot import SlotBrief


class GameCreate(BaseModel):
    court_id: int = Field(gt=0)
    sport_type: SportType
    start_time: datetime | None = Field(
        default=None,
        description="ISO 8601; без смещения трактуется как время APP_TIMEZONE. Для платного сбора берётся из слота",
    )
    slot_id: int | None = Field(default=None, gt=0, description="Слот аренды — обязателен для коммерческого корта")
    required_players: int = Field(ge=2, le=30, description="Сколько игроков нужно всего, включая создателя")
    comment: str = Field(default="", max_length=500)
    creator_max_id: MaxUserId
    creator_name: PersonName
    creator_username: Username = None

    @model_validator(mode="after")
    def start_or_slot(self) -> GameCreate:
        if self.slot_id is None and self.start_time is None:
            raise ValueError("Укажите время начала или слот аренды")
        return self


class PlayerRequest(BaseModel):
    """Кто вступает в лобби или выходит из него."""

    user_max_id: MaxUserId
    user_name: PersonName
    username: Username = None


class PayRequest(BaseModel):
    """Взнос доли участника на эскроу-счёт (тестовая оплата через СБП)."""

    user_max_id: MaxUserId
    user_name: PersonName | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2, description="Сумма доли; если не указана — рассчитывается сервером")
    payment_method: Literal["sbp_mock"] = "sbp_mock"


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_max_id: str
    user_name: str
    joined_at: datetime
    has_paid: bool = False
    paid_amount: Money = ZERO
    paid_at: datetime | None = None


class GameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    court_id: int
    creator_max_id: str
    sport_type: str
    start_time: datetime
    required_players: int
    current_players: int
    status: str
    comment: str
    created_at: datetime
    participants: list[ParticipantRead] = Field(default_factory=list)
    slot_id: int | None = None
    slot: SlotBrief | None = None
    escrow_account_id: str | None = None
    total_cost: Money = ZERO
    collected_amount: Money = ZERO
    payment_status: str = "pending"
    payment_deadline: datetime | None = None
    booking_reference: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spots_left(self) -> int:
        return max(0, self.required_players - self.current_players)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return GAME_STATUS_LABELS.get(self.status, self.status)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_paid(self) -> bool:
        return self.escrow_account_id is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def payment_status_label(self) -> str | None:
        return PAYMENT_STATUS_LABELS.get(self.payment_status) if self.is_paid else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def share_amount(self) -> Money:
        """Доля одного игрока: стоимость корта / число игроков (последний платит остаток до копейки)."""
        return to_money(self.total_cost / self.required_players) if self.is_paid else ZERO

    @computed_field  # type: ignore[prop-decorator]
    @property
    def paid_count(self) -> int:
        return sum(1 for participant in self.participants if participant.has_paid)


class GameCourt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    address: str
    latitude: float
    longitude: float


class GameWithCourt(GameRead):
    court: GameCourt


class JoinResponse(BaseModel):
    game: GameWithCourt
    joined: bool = Field(description="False — пользователь уже был в составе")
    confirmed: bool = Field(description="True — этим вступлением набран кворум")
    message: str


class LeaveResponse(BaseModel):
    game: GameWithCourt
    message: str


class EscrowTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    kind: str
    amount: Money
    method: str
    user_max_id: str | None
    created_at: datetime


class PayResponse(BaseModel):
    game: GameWithCourt
    transaction: EscrowTransactionRead
    booked: bool = Field(description="True — этим взносом собрано 100%, корт выкуплен")
    booking_reference: str | None = None
    message: str


class EscrowRead(BaseModel):
    """Выписка по виртуальному эскроу-счёту сбора."""

    game_id: int
    escrow_account_id: str
    payment_status: str
    payment_status_label: str
    total_cost: Money
    collected_amount: Money
    balance: Money
    payment_deadline: datetime | None
    booking_reference: str | None
    provider: str
    transactions: list[EscrowTransactionRead]
