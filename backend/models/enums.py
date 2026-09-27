"""Справочники предметной области и их русские подписи (используются API и ботом)."""

from __future__ import annotations

from enum import StrEnum


class SportType(StrEnum):
    BASKETBALL = "basketball"
    FOOTBALL = "football"
    VOLLEYBALL = "volleyball"
    TABLE_TENNIS = "table_tennis"
    WORKOUT = "workout"
    TENNIS = "tennis"
    PADEL = "padel"


class SurfaceType(StrEnum):
    RUBBER = "rubber"
    ASPHALT = "asphalt"
    ARTIFICIAL_TURF = "artificial_turf"
    HARD = "hard"
    PARQUET = "parquet"


class GameStatus(StrEnum):
    RECRUITING = "recruiting"
    CONFIRMED = "confirmed"
    BOOKED = "booked"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    FUNDED = "funded"
    PAID_TO_COURT = "paid_to_court"
    REFUNDED = "refunded"


class EscrowTxKind(StrEnum):
    DEPOSIT = "deposit"
    PAYOUT = "payout"
    REFUND = "refund"


class SlotStatus(StrEnum):
    FREE = "free"
    RESERVED = "reserved"
    BOOKED = "booked"


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


# Сбор считается активным (виден на карте, в него можно вступать или он ещё не сыгран).
ACTIVE_GAME_STATUSES: tuple[str, ...] = (
    GameStatus.RECRUITING.value,
    GameStatus.CONFIRMED.value,
    GameStatus.BOOKED.value,
)

SPORT_LABELS: dict[str, str] = {
    SportType.BASKETBALL: "Баскетбол",
    SportType.FOOTBALL: "Футбол",
    SportType.VOLLEYBALL: "Волейбол",
    SportType.TABLE_TENNIS: "Настольный теннис",
    SportType.WORKOUT: "Воркаут",
    SportType.TENNIS: "Теннис",
    SportType.PADEL: "Падел",
}

SPORT_EMOJI: dict[str, str] = {
    SportType.BASKETBALL: "🏀",
    SportType.FOOTBALL: "⚽",
    SportType.VOLLEYBALL: "🏐",
    SportType.TABLE_TENNIS: "🏓",
    SportType.WORKOUT: "💪",
    SportType.TENNIS: "🎾",
    SportType.PADEL: "🥎",
}

# Ключевые слова для распознавания вида спорта в свободном тексте боту.
# Порядок важен: «настольный теннис» проверяется раньше «тенниса».
SPORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    SportType.BASKETBALL: ("баскет", "стритбол", "basket", "3х3", "3x3"),
    SportType.FOOTBALL: ("футбол", "футик", "football", "soccer", "мини-футбол"),
    SportType.VOLLEYBALL: ("волейбол", "волик", "volley"),
    SportType.TABLE_TENNIS: ("настольн", "пинг", "ping", "table tennis"),
    SportType.PADEL: ("падел", "падл", "padel"),
    SportType.TENNIS: ("теннис", "tennis", "корт"),
    SportType.WORKOUT: ("воркаут", "турник", "workout", "брусья", "кроссфит"),
}

SURFACE_LABELS: dict[str, str] = {
    SurfaceType.RUBBER: "резиновое",
    SurfaceType.ASPHALT: "асфальт",
    SurfaceType.ARTIFICIAL_TURF: "искусственный газон",
    SurfaceType.HARD: "хард",
    SurfaceType.PARQUET: "паркет",
    "acrylic": "акрил",
    "artificial_grass": "искусственный газон",
    "panoramic_glass_turf": "панорамное стекло / газон",
    "padel_turf": "падел-газон",
    "clay": "грунт",
    "tera_flex": "терафлекс",
}

GAME_STATUS_LABELS: dict[str, str] = {
    GameStatus.RECRUITING: "Идёт набор",
    GameStatus.CONFIRMED: "Состав собран",
    GameStatus.BOOKED: "Корт забронирован",
    GameStatus.FINISHED: "Завершён",
    GameStatus.CANCELLED: "Отменён",
}

PAYMENT_STATUS_LABELS: dict[str, str] = {
    PaymentStatus.PENDING: "Идёт сбор средств",
    PaymentStatus.FUNDED: "Сумма собрана",
    PaymentStatus.PAID_TO_COURT: "Оплачено арендодателю",
    PaymentStatus.REFUNDED: "Средства возвращены",
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
