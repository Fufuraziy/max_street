from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from models.enums import SportType, SurfaceType
from schemas.common import Money
from schemas.defect import DefectRead
from schemas.game import GameRead


def _clean_text(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 3:
        raise ValueError("Минимум 3 символа")
    return value


def normalize_website(value: str | None) -> str | None:
    """«example.ru» → «https://example.ru». Пустая строка — сайта нет."""
    value = (value or "").strip()
    if not value:
        return None
    if "://" not in value:
        value = f"https://{value}"
    parts = urlsplit(value)
    host = parts.hostname or ""
    if parts.scheme not in {"http", "https"} or "." not in host or any(ch.isspace() for ch in value):
        raise ValueError("укажите адрес сайта, например example.ru")
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
    website: str | None = Field(default=None, max_length=300, description="Сайт организации (необязательно)")

    @field_validator("sport_types")
    @classmethod
    def unique_sports(cls, value: list[SportType]) -> list[SportType]:
        return list(dict.fromkeys(value))

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("website")
    @classmethod
    def check_website(cls, value: str | None) -> str | None:
        return normalize_website(value)


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
    is_commercial: bool = Field(default=False, description="Коммерческий корт: аренда по слотам и оплата через эскроу")
    rating: float
    description: str
    website: str | None = Field(default=None, description="Сайт организации")
    active_games_today: int = Field(default=0, description="Активные сборы на сегодня")
    price_from: Money | None = Field(default=None, description="Минимальная цена свободного слота аренды")


class CourtDetail(CourtRead):
    games: list[GameRead] = Field(default_factory=list, description="Активные и предстоящие сборы")
    defects: list[DefectRead] = Field(default_factory=list, description="Зафиксированные неисправности")
