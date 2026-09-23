from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.timeutils import utcnow
from models.enums import GameStatus

if TYPE_CHECKING:
    from models.court import Court


class Game(Base):
    """Лобби (сбор) на игру."""

    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_court_status_start", "court_id", "status", "start_time"),
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

    court: Mapped[Court] = relationship(back_populates="games")
    participants: Mapped[list[GameParticipant]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="GameParticipant.id",
    )

    @property
    def spots_left(self) -> int:
        return max(0, self.required_players - self.current_players)


class GameParticipant(Base):
    """Участник лобби."""

    __tablename__ = "game_participants"
    __table_args__ = (UniqueConstraint("game_id", "user_max_id", name="uq_game_participant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_max_id: Mapped[str] = mapped_column(String(64), index=True)
    user_name: Mapped[str] = mapped_column(String(100))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    game: Mapped[Game] = relationship(back_populates="participants")
