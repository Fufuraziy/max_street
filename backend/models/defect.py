from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.timeutils import utcnow
from models.enums import DefectStatus

if TYPE_CHECKING:
    from models.court import Court


class CourtDefect(Base):
    """Заявка о неисправности инфраструктуры площадки."""

    __tablename__ = "court_defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id", ondelete="CASCADE"), index=True)
    user_max_id: Mapped[str] = mapped_column(String(64), index=True)
    defect_type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=DefectStatus.REPORTED.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    court: Mapped[Court] = relationship(back_populates="defects")
