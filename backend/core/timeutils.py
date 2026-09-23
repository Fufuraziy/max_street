"""Работа со временем: всё храним в UTC, «сегодня» и подписи считаем в часовом поясе города."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.config import settings

# Сбор считается активным ещё 2 часа после начала (игра идёт).
GAME_ACTIVE_GRACE = timedelta(hours=2)

_WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
_MONTHS = ("янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(dt: datetime) -> datetime:
    """Наивное время трактуем как локальное время города (APP_TIMEZONE)."""
    return dt.replace(tzinfo=settings.tz) if dt.tzinfo is None else dt


def to_local(dt: datetime) -> datetime:
    return ensure_aware(dt).astimezone(settings.tz)


def local_now() -> datetime:
    return utcnow().astimezone(settings.tz)


def today_bounds() -> tuple[datetime, datetime]:
    """Начало и конец текущих суток в часовом поясе города."""
    start = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def active_since() -> datetime:
    """Самое раннее время начала, при котором сбор ещё считается активным."""
    return utcnow() - GAME_ACTIVE_GRACE


def human_datetime(dt: datetime) -> str:
    """«сегодня в 19:00», «завтра в 18:30», «пт, 26 сен в 19:00»."""
    local = to_local(dt)
    delta_days = (local.date() - local_now().date()).days
    time_part = local.strftime("%H:%M")
    if delta_days == 0:
        return f"сегодня в {time_part}"
    if delta_days == 1:
        return f"завтра в {time_part}"
    if delta_days == -1:
        return f"вчера в {time_part}"
    return f"{_WEEKDAYS[local.weekday()]}, {local.day} {_MONTHS[local.month - 1]} в {time_part}"


def short_datetime(dt: datetime) -> str:
    """Короткая подпись для кнопок: «сегодня 19:00», «завтра 18:30», «26.09 19:00»."""
    local = to_local(dt)
    delta_days = (local.date() - local_now().date()).days
    time_part = local.strftime("%H:%M")
    if delta_days == 0:
        return f"сегодня {time_part}"
    if delta_days == 1:
        return f"завтра {time_part}"
    return f"{local.strftime('%d.%m')} {time_part}"
