from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.common import Money


class SlotBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    end_time: datetime
    price: Money
    duration_minutes: int


class SlotRead(SlotBrief):
    court_id: int
    is_booked: bool
    status: str = Field(description="free — свободно, reserved — удерживается эскроу-сбором, booked — занято")
    is_available: bool
