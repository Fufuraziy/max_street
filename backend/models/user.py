from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.timeutils import utcnow


class User(Base):
    """Пользователь MAX (создаётся/обновляется при любом действии в боте или мини-приложении)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    max_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reliability_score: Mapped[float] = mapped_column(default=100.0, server_default="100.0")
    games_attended: Mapped[int] = mapped_column(default=0, server_default="0")
    games_missed: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
