"""Эндпоинт погоды: текущая и прогноз на время сбора по координатам площадки."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from core.errors import ValidationFailedError
from services.weather_service import fetch_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", summary="Погода сейчас или прогноз на время сбора (Open-Meteo)")
async def get_weather(
    lat: float = Query(59.9386, ge=-90, le=90, description="Широта"),
    lon: float = Query(30.3141, ge=-180, le=180, description="Долгота"),
    time: str | None = Query(None, description="ISO-строка даты и времени сбора; без неё — текущая погода"),
) -> dict[str, Any]:
    """Без `time` — текущая погода. С `time` — почасовой прогноз на ближайший час.

    404 — время вне горизонта прогноза (16 дней), 503 — сервис погоды недоступен.
    """
    target_dt = None
    if time:
        try:
            target_dt = datetime.fromisoformat(time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationFailedError("Время: ожидается ISO 8601, например 2026-09-30T19:00:00+03:00") from exc
    return await fetch_weather(lat, lon, target_dt)
