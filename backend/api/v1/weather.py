"""Эндпоинт погоды: текущая и прогноз на время сбора по координатам площадки."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Query
from services.weather_service import fetch_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("")
async def get_weather(
    lat: float = Query(59.9386, description="Широта"),
    lon: float = Query(30.3141, description="Долгота"),
    time: str | None = Query(None, description="ISO-строка даты и времени сбора для прогноза"),
) -> dict[str, Any]:
    target_dt = None
    if time:
        try:
            target_dt = datetime.fromisoformat(time.replace("Z", "+00:00"))
        except ValueError:
            target_dt = None

    return await fetch_weather(lat, lon, target_dt)
