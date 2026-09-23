from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.timeutils import utcnow


class EscrowTransaction(Base):
    """Журнал движения средств по эскроу-счёту сбора: взносы, выплата арендодателю, возвраты.

    Баланс счёта = взносы − выплаты − возвраты; поле games.collected_amount — денормализованный итог взносов.
    """

    __tablename__ = "escrow_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    escrow_account_id: Mapped[str] = mapped_column(String(64), index=True)
    user_max_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    method: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
