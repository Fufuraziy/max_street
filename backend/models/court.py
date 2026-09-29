from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text, false
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.timeutils import utcnow

if TYPE_CHECKING:
    from models.defect import CourtDefect
    from models.game import Game
    from models.slot import CourtSlot


class Court(Base):
    """Спортивная площадка (спот) на карте. Коммерческие корты сдаются в аренду по слотам."""

    __tablename__ = "courts"
    __table_args__ = (
        Index("ix_courts_lat_lon", "latitude", "longitude"),
        Index("ix_courts_sport_types", "sport_types", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    sport_types: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    surface_type: Mapped[str] = mapped_column(String(32))
    has_lighting: Mapped[bool] = mapped_column(Boolean, default=False)
    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)
    is_commercial: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    games: Mapped[list[Game]] = relationship(
        back_populates="court", cascade="all, delete-orphan", passive_deletes=True
    )
    defects: Mapped[list[CourtDefect]] = relationship(
        back_populates="court", cascade="all, delete-orphan", passive_deletes=True
    )
    slots: Mapped[list[CourtSlot]] = relationship(
        back_populates="court", cascade="all, delete-orphan", passive_deletes=True
    )
