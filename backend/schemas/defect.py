from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from models.enums import DEFECT_LABELS, DEFECT_STATUS_LABELS, DefectStatus, DefectType
from schemas.common import MaxUserId, PersonName


class DefectCreate(BaseModel):
    user_max_id: MaxUserId
    user_name: PersonName | None = None
    defect_type: DefectType
    description: str = Field(default="", max_length=1000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class DefectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    court_id: int
    defect_type: str
    description: str
    status: str
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def defect_label(self) -> str:
        return DEFECT_LABELS.get(self.defect_type, self.defect_type)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return DEFECT_STATUS_LABELS.get(self.status, self.status)


class DefectCourt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    address: str


class DefectWithCourt(DefectRead):
    court: DefectCourt


class DefectStatusUpdate(BaseModel):
    status: DefectStatus
