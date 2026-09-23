from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from models.enums import SportType, SurfaceType
from schemas.defect import DefectRead
from schemas.game import GameRead


def _clean_text(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 3:
        raise ValueError("Минимум 3 символа")
    return value


CleanTitle = Annotated[str, Field(min_length=3, max_length=200), AfterValidator(_clean_text)]
CleanAddress = Annotated[str, Field(min_length=3, max_length=300), AfterValidator(_clean_text)]


class CourtCreate(BaseModel):
    """Новая площадка от пользователя (краудсорсинг)."""

    title: CleanTitle
    sport_types: list[SportType] = Field(min_length=1, max_length=5)
    address: CleanAddress
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surface_type: SurfaceType
    has_lighting: bool = False
    is_indoor: bool = False
    description: str = Field(default="", max_length=2000)

    @field_validator("sport_types")
    @classmethod
    def unique_sports(cls, value: list[SportType]) -> list[SportType]:
        return list(dict.fromkeys(value))

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class CourtBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    address: str
    latitude: float
    longitude: float


class CourtRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    sport_types: list[str]
    address: str
    latitude: float
    longitude: float
    surface_type: str
    has_lighting: bool
    is_indoor: bool
    rating: float
    description: str
    active_games_today: int = Field(default=0, description="Активные сборы на сегодня")


class CourtDetail(CourtRead):
    games: list[GameRead] = Field(default_factory=list, description="Активные и предстоящие сборы")
    defects: list[DefectRead] = Field(default_factory=list, description="Зафиксированные неисправности")
