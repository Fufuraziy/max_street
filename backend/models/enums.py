"""Справочники предметной области и их русские подписи (используются API и ботом)."""

from __future__ import annotations

from enum import StrEnum


class SportType(StrEnum):
    BASKETBALL = "basketball"
    FOOTBALL = "football"
    VOLLEYBALL = "volleyball"
    TABLE_TENNIS = "table_tennis"
    WORKOUT = "workout"


class SurfaceType(StrEnum):
    RUBBER = "rubber"
    ASPHALT = "asphalt"
    ARTIFICIAL_TURF = "artificial_turf"


class GameStatus(StrEnum):
    RECRUITING = "recruiting"
    CONFIRMED = "confirmed"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class DefectType(StrEnum):
    BROKEN_RING = "broken_ring"
    SURFACE_DAMAGE = "surface_damage"
    LIGHTING_BROKEN = "lighting_broken"
    NET_MISSING = "net_missing"
    TRASH = "trash"


class DefectStatus(StrEnum):
    REPORTED = "reported"
    SENT_TO_CITY = "sent_to_city"
    RESOLVED = "resolved"


ACTIVE_GAME_STATUSES: tuple[str, ...] = (GameStatus.RECRUITING.value, GameStatus.CONFIRMED.value)

SPORT_LABELS: dict[str, str] = {
    SportType.BASKETBALL: "Баскетбол",
    SportType.FOOTBALL: "Футбол",
    SportType.VOLLEYBALL: "Волейбол",
    SportType.TABLE_TENNIS: "Настольный теннис",
    SportType.WORKOUT: "Воркаут",
}

SPORT_EMOJI: dict[str, str] = {
    SportType.BASKETBALL: "🏀",
    SportType.FOOTBALL: "⚽",
    SportType.VOLLEYBALL: "🏐",
    SportType.TABLE_TENNIS: "🏓",
    SportType.WORKOUT: "💪",
}

# Ключевые слова для распознавания вида спорта в свободном тексте боту.
SPORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    SportType.BASKETBALL: ("баскет", "стритбол", "basket", "3х3", "3x3"),
    SportType.FOOTBALL: ("футбол", "футик", "football", "soccer", "мини-футбол"),
    SportType.VOLLEYBALL: ("волейбол", "волик", "volley"),
    SportType.TABLE_TENNIS: ("теннис", "пинг", "tennis", "ping"),
    SportType.WORKOUT: ("воркаут", "турник", "workout", "брусья", "кроссфит"),
}

SURFACE_LABELS: dict[str, str] = {
    SurfaceType.RUBBER: "резиновое",
    SurfaceType.ASPHALT: "асфальт",
    SurfaceType.ARTIFICIAL_TURF: "искусственный газон",
}

GAME_STATUS_LABELS: dict[str, str] = {
    GameStatus.RECRUITING: "Идёт набор",
    GameStatus.CONFIRMED: "Состав собран",
    GameStatus.FINISHED: "Завершён",
    GameStatus.CANCELLED: "Отменён",
}

DEFECT_LABELS: dict[str, str] = {
    DefectType.BROKEN_RING: "Сломано кольцо или щит",
    DefectType.SURFACE_DAMAGE: "Яма или повреждение покрытия",
    DefectType.LIGHTING_BROKEN: "Не работает освещение",
    DefectType.NET_MISSING: "Нет сетки",
    DefectType.TRASH: "Мусор на площадке",
}

DEFECT_STATUS_LABELS: dict[str, str] = {
    DefectStatus.REPORTED: "Передано в районные службы",
    DefectStatus.SENT_TO_CITY: "В работе у городских служб",
    DefectStatus.RESOLVED: "Устранено",
}


def sport_label(sport: str) -> str:
    return SPORT_LABELS.get(sport, sport)


def sport_emoji(sport: str) -> str:
    return SPORT_EMOJI.get(sport, "🏅")


def detect_sport(text: str) -> str | None:
    lowered = text.lower()
    for sport, keywords in SPORT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return str(sport)
    return None
