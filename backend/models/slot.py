from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.court import Court


class CourtSlot(Base):
    """Окно аренды коммерческого корта из расписания арендодателя."""

    __tablename__ = "court_slots"
    __table_args__ = (
        UniqueConstraint("court_id", "start_time", name="uq_court_slots_court_start"),
        Index("ix_court_slots_court_start", "court_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    court: Mapped[Court] = relationship(back_populates="slots")

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() // 60)
