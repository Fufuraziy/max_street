"""Сервис погоды: текущие условия и почасовой прогноз на время сбора (Open-Meteo).

Open-Meteo бесплатен, не требует ключа и отдаёт почасовой прогноз на 16 дней вперёд.
Прогноз по точке загружается одним запросом и кешируется целиком, поэтому все сборы
на площадке используют одни данные. Время сбора переводится в часовой пояс города
(APP_TIMEZONE) — в нём же Open-Meteo возвращает почасовую сетку.

Если время за пределами горизонта прогноза, сервис честно отвечает «недоступно»
(404), а не подставляет сегодняшнюю погоду. Если Open-Meteo недоступен — 503.
Фоновая задача раз в 30 минут обновляет прогноз для всех площадок, поэтому
синхронное чтение для карточек бота работает из кеша без сетевых запросов.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select

from core.config import settings
from core.database import SessionLocal
from core.errors import DomainError, NotFoundError
from core.timeutils import ensure_aware, local_now

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16
CACHE_TTL_SECONDS = 30 * 60  # свежесть прогноза
STALE_TTL_SECONDS = 3 * 60 * 60  # сколько можно отдавать старый прогноз, если API недоступен
REFRESH_INTERVAL_SECONDS = 30 * 60
REQUEST_TIMEOUT_SECONDS = 3.5
BATCH_SIZE = 50
LOCATION_LABEL = "Санкт-Петербург"

HOURLY_FIELDS = "temperature_2m,apparent_temperature,precipitation_probability,weather_code"
CURRENT_FIELDS = "temperature_2m,apparent_temperature,weather_code"


class WeatherUnavailableError(DomainError):
    status_code = 503


# (lat, lon) с округлением до 0.01° → (время загрузки, разобранный прогноз)
_FORECASTS: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
_PENDING: set[tuple[float, float]] = set()


def _point(lat: float, lon: float) -> tuple[float, float]:
    return round(lat, 2), round(lon, 2)


def describe_wmo(code: int) -> tuple[str, str]:
    """Код погоды WMO (как в Open-Meteo) → описание и иконка."""
    if code == 0:
        return "Ясно", "☀️"
    if code == 1:
        return "Преимущественно ясно", "🌤️"
    if code == 2:
        return "Переменная облачность", "⛅"
    if code == 3:
        return "Пасмурно", "☁️"
    if code in (45, 48):
        return "Туман", "🌫️"
    if code in (51, 53, 55):
        return "Морось", "🌦️"
    if code in (56, 57):
        return "Ледяная морось", "🌧️"
    if code in (61, 63):
        return "Дождь", "🌧️"
    if code == 65:
        return "Сильный дождь", "🌧️"
    if code in (66, 67):
        return "Ледяной дождь", "🌧️"
    if code in (71, 73, 77):
        return "Снег", "🌨️"
    if code == 75:
        return "Сильный снег", "🌨️"
    if code in (80, 81):
        return "Ливень", "🌦️"
    if code == 82:
        return "Сильный ливень", "⛈️"
    if code in (85, 86):
        return "Снегопад", "🌨️"
    if code == 95:
        return "Гроза", "⛈️"
    if code in (96, 99):
        return "Гроза с градом", "⛈️"
    return "Переменная облачность", "⛅"


def _is_wet(code: int) -> bool:
    return 51 <= code <= 67 or 80 <= code <= 82 or code >= 95


def _build_result(temp: float, feels: float | None, code: int, precip_chance: int) -> dict[str, Any]:
    temp_c = int(round(temp))
    description, icon = describe_wmo(code)
    rain_note = f", вероятность осадков {precip_chance}%" if precip_chance > 20 else ", без осадков"
    return {
        "temp_c": temp_c,
        "feels_like_c": int(round(feels)) if feels is not None else temp_c,
        "description": description,
        "icon": icon,
        "precipitation_chance": precip_chance,
        "is_rain": _is_wet(code) or precip_chance >= 40,
        "summary": f"{'+' if temp_c > 0 else ''}{temp_c}°C, {description.lower()}{rain_note}",
        "location": LOCATION_LABEL,
    }


def _parse_forecast(raw: dict[str, Any]) -> dict[str, Any]:
    """Ответ Open-Meteo → {"hourly": {"YYYY-MM-DDTHH:00": {...}}, "current": {...}}."""
    hourly_raw = raw.get("hourly") or {}
    hours: dict[str, dict[str, Any]] = {}
    for index, stamp in enumerate(hourly_raw.get("time") or []):
        temp = _safe_get(hourly_raw.get("temperature_2m"), index)
        if temp is None:
            continue
        hours[stamp] = {
            "temp": temp,
            "feels": _safe_get(hourly_raw.get("apparent_temperature"), index),
            "pop": _safe_get(hourly_raw.get("precipitation_probability"), index) or 0,
            "code": _safe_get(hourly_raw.get("weather_code"), index) or 0,
        }
    return {"hourly": hours, "current": raw.get("current") or {}}


def _safe_get(values: list[Any] | None, index: int) -> Any:
    if not values or index >= len(values):
        return None
    return values[index]


async def _request(latitudes: list[float], longitudes: list[float]) -> list[dict[str, Any]]:
    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat in latitudes),
        "longitude": ",".join(f"{lon:.4f}" for lon in longitudes),
        "hourly": HOURLY_FIELDS,
        "current": CURRENT_FIELDS,
        "timezone": settings.app_timezone,
        "forecast_days": FORECAST_DAYS,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
    # Для нескольких точек Open-Meteo возвращает массив, для одной — объект.
    return data if isinstance(data, list) else [data]


async def _load_forecast(lat: float, lon: float) -> dict[str, Any] | None:
    """Прогноз по точке: из свежего кеша или новым запросом; при сбое — устаревший кеш."""
    point = _point(lat, lon)
    cached = _FORECASTS.get(point)
    now = time.time()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    try:
        raw = (await _request([lat], [lon]))[0]
        forecast = _parse_forecast(raw)
        _FORECASTS[point] = (now, forecast)
        return forecast
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logger.warning("Open-Meteo недоступен для %s: %s", point, exc)
        if cached and now - cached[0] < STALE_TTL_SECONDS:
            return cached[1]
        return None


def _hour_key(target_time: datetime) -> str:
    """Время сбора → ближайший час в часовом поясе города, формат сетки Open-Meteo."""
    local = ensure_aware(target_time).astimezone(settings.tz) + timedelta(minutes=30)
    return local.strftime("%Y-%m-%dT%H:00")


def _forecast_for(forecast: dict[str, Any], target_time: datetime | None) -> dict[str, Any] | None:
    hours = forecast["hourly"]
    if target_time is None:
        current = forecast["current"]
        now_hour = hours.get(_hour_key(local_now())) or {}
        temp = current.get("temperature_2m", now_hour.get("temp"))
        if temp is None:
            return None
        return _build_result(
            temp,
            current.get("apparent_temperature", now_hour.get("feels")),
            int(current.get("weather_code", now_hour.get("code", 0)) or 0),
            int(now_hour.get("pop") or 0),
        )
    slot = hours.get(_hour_key(target_time))
    if slot is None:
        return None
    return _build_result(slot["temp"], slot["feels"], int(slot["code"]), int(slot["pop"]))


async def fetch_weather(lat: float, lon: float, target_time: datetime | None = None) -> dict[str, Any]:
    """Текущая погода или прогноз на время сбора. Бросает 404, если время вне горизонта прогноза."""
    forecast = await _load_forecast(lat, lon)
    if forecast is None:
        raise WeatherUnavailableError("Сервис погоды временно недоступен")
    result = _forecast_for(forecast, target_time)
    if result is None:
        raise NotFoundError("Прогноз на это время пока недоступен: он появляется примерно за две недели")
    return result


def get_forecast_summary_sync(lat: float, lon: float, target_time: datetime | None = None) -> str | None:
    """Строка погоды для карточки бота — только из кеша, без сетевых запросов.

    Если прогноза по точке ещё нет, запускает его загрузку в фоне и возвращает None
    (карточка покажется без строки погоды, следующее сообщение уже будет с ней).
    """
    point = _point(lat, lon)
    cached = _FORECASTS.get(point)
    if cached is None or time.time() - cached[0] >= STALE_TTL_SECONDS:
        _schedule_load(lat, lon)
        if cached is None:
            return None
    result = _forecast_for(cached[1], target_time)
    return result["summary"] if result else None


def _schedule_load(lat: float, lon: float) -> None:
    point = _point(lat, lon)
    if point in _PENDING:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _PENDING.add(point)
    task = loop.create_task(_load_forecast(lat, lon))
    task.add_done_callback(lambda _: _PENDING.discard(point))


async def refresh_courts_forecasts() -> int:
    """Обновляет прогноз для всех площадок пачками (одним запросом на до 50 точек)."""
    from models import Court  # локальный импорт: сервис не должен тянуть модели при импорте

    async with SessionLocal() as session:
        rows = (await session.execute(select(Court.latitude, Court.longitude))).all()
    points = sorted({_point(lat, lon) for lat, lon in rows})
    refreshed = 0
    now = time.time()
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        try:
            raws = await _request([p[0] for p in batch], [p[1] for p in batch])
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Не удалось обновить прогноз погоды для площадок: %s", exc)
            continue
        for point, raw in zip(batch, raws):
            _FORECASTS[point] = (now, _parse_forecast(raw))
            refreshed += 1
    return refreshed


async def weather_refresher() -> None:
    """Фоновая задача: держит прогноз по всем площадкам свежим для бота и API."""
    while True:
        try:
            count = await refresh_courts_forecasts()
            logger.info("Прогноз погоды обновлён для %s точек", count)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - фоновая задача не должна падать
            logger.exception("Ошибка обновления прогноза погоды")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


async def stop_task(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
