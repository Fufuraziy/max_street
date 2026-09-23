from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from models.enums import GAME_STATUS_LABELS, SportType
from schemas.common import MaxUserId, PersonName, Username


class GameCreate(BaseModel):
    court_id: int = Field(gt=0)
    sport_type: SportType
    start_time: datetime = Field(description="ISO 8601; без смещения трактуется как время APP_TIMEZONE")
    required_players: int = Field(ge=2, le=30, description="Сколько игроков нужно всего, включая создателя")
    comment: str = Field(default="", max_length=500)
    creator_max_id: MaxUserId
    creator_name: PersonName
    creator_username: Username = None


class PlayerRequest(BaseModel):
    """Кто вступает в лобби или выходит из него."""

    user_max_id: MaxUserId
    user_name: PersonName
    username: Username = None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_max_id: str
    user_name: str
    joined_at: datetime


class GameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    court_id: int
    creator_max_id: str
    sport_type: str
    start_time: datetime
    required_players: int
    current_players: int
    status: str
    comment: str
    created_at: datetime
    participants: list[ParticipantRead] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spots_left(self) -> int:
        return max(0, self.required_players - self.current_players)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return GAME_STATUS_LABELS.get(self.status, self.status)


class GameCourt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    address: str
    latitude: float
    longitude: float


class GameWithCourt(GameRead):
    court: GameCourt


class JoinResponse(BaseModel):
    game: GameWithCourt
    joined: bool = Field(description="False — пользователь уже был в составе")
    confirmed: bool = Field(description="True — этим вступлением набран кворум")
    message: str


class LeaveResponse(BaseModel):
    game: GameWithCourt
    message: str
