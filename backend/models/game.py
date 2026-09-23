from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.timeutils import utcnow
from models.enums import GameStatus, PaymentStatus

if TYPE_CHECKING:
    from models.court import Court
    from models.slot import CourtSlot


class Game(Base):
    """Лобби (сбор) на игру. Для коммерческого корта — с эскроу-счётом и привязкой к слоту аренды."""

    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_court_status_start", "court_id", "status", "start_time"),
        # Один слот аренды может удерживать только одно активное лобби.
        Index(
            "uq_games_active_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("slot_id IS NOT NULL AND status IN ('recruiting', 'confirmed', 'booked')"),
        ),
        CheckConstraint("required_players >= 2", name="ck_games_required_players"),
        CheckConstraint("current_players >= 0", name="ck_games_current_players"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id", ondelete="CASCADE"), index=True)
    creator_max_id: Mapped[str] = mapped_column(String(64), index=True)
    sport_type: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    required_players: Mapped[int] = mapped_column(Integer)
    current_players: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default=GameStatus.RECRUITING.value, index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # --- Аренда и эскроу (только для коммерческих кортов) ---
    slot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("court_slots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    escrow_account_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default="0")
    collected_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default="0")
    payment_status: Mapped[str] = mapped_column(
        String(32), default=PaymentStatus.PENDING.value, server_default=PaymentStatus.PENDING.value
    )
    payment_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    booking_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)

    court: Mapped[Court] = relationship(back_populates="games")
    slot: Mapped[CourtSlot | None] = relationship()
    participants: Mapped[list[GameParticipant]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="GameParticipant.id",
    )

    @property
    def spots_left(self) -> int:
        return max(0, self.required_players - self.current_players)

    @property
    def is_paid(self) -> bool:
        return self.escrow_account_id is not None


class GameParticipant(Base):
    """Участник лобби и его взнос в эскроу."""

    __tablename__ = "game_participants"
    __table_args__ = (UniqueConstraint("game_id", "user_max_id", name="uq_game_participant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_max_id: Mapped[str] = mapped_column(String(64), index=True)
    user_name: Mapped[str] = mapped_column(String(100))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    has_paid: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default="0")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    game: Mapped[Game] = relationship(back_populates="participants")
