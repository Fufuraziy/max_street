"""Сервис погоды: текущие условия и прогноз на время сбора по координатам площадки."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
import httpx

logger = logging.getLogger(__name__)

# Кеш погоды: (lat_round, lon_round, date_hour_key) -> (timestamp, data)
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 900  # 15 минут

WEATHER_TRANSLATIONS: dict[str, tuple[str, str]] = {
    "Sunny": ("Ясно", "☀️"),
    "Clear": ("Ясно", "☀️"),
    "Partly cloudy": ("Переменная облачность", "⛅"),
    "Partly Cloudy": ("Переменная облачность", "⛅"),
    "Cloudy": ("Облачно", "☁️"),
    "Overcast": ("Пасмурно", "☁️"),
    "Mist": ("Дымка", "🌫️"),
    "Fog": ("Туман", "🌫️"),
    "Light rain": ("Небольшой дождь", "🌦️"),
    "Light Rain": ("Небольшой дождь", "🌦️"),
    "Moderate rain": ("Умеренный дождь", "🌧️"),
    "Heavy rain": ("Сильный дождь", "🌧️"),
    "Patchy rain possible": ("Возможен кратковременный дождь", "🌦️"),
    "Patchy light rain": ("Местами небольшой дождь", "🌦️"),
    "Thundery outbreaks possible": ("Возможна гроза", "⛈️"),
    "Light snow": ("Небольшой снег", "🌨️"),
    "Moderate snow": ("Снегопад", "🌨️"),
}


def _translate_weather(raw_desc: str) -> tuple[str, str]:
    raw_desc = raw_desc.strip()
    if raw_desc in WEATHER_TRANSLATIONS:
        return WEATHER_TRANSLATIONS[raw_desc]
    for key, val in WEATHER_TRANSLATIONS.items():
        if key.lower() in raw_desc.lower():
            return val
    return (raw_desc, "⛅")


def _fallback_weather(target_time: datetime | None = None) -> dict[str, Any]:
    hour = target_time.hour if target_time else datetime.now().hour
    # Базовые дневные/ночные реалистичные температуры для СПб
    temp = 14 if 9 <= hour <= 21 else 9
    return {
        "temp_c": temp,
        "feels_like_c": temp - 1,
        "description": "Переменная облачность",
        "icon": "⛅",
        "precipitation_chance": 10,
        "is_rain": False,
        "summary": f"+{temp}°C, переменная облачность, без осадков",
        "location": "Санкт-Петербург",
    }


async def fetch_weather(lat: float, lon: float, target_time: datetime | None = None) -> dict[str, Any]:
    """Возвращает погоду для указанных координат и (опционально) времени сбора."""
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)
    hour_key = f"{target_time.strftime('%Y-%m-%d-%H')}" if target_time else "current"
    cache_key = f"{lat_r}:{lon_r}:{hour_key}"

    now_ts = time.time()
    if cache_key in _CACHE:
        cached_ts, cached_val = _CACHE[cache_key]
        if now_ts - cached_ts < CACHE_TTL_SECONDS:
            return cached_val

    try:
        url = f"https://wttr.in/{lat:.4f},{lon:.4f}?format=j1"
        async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
            resp = await client.get(url, headers={"User-Agent": "curl/7.68.0"})
            if resp.status_code == 200:
                data = resp.json()
                
                # Если запрошено конкретное время сбора в будущем
                if target_time and "weather" in data:
                    target_date_str = target_time.strftime("%Y-%m-%d")
                    target_hour = target_time.hour
                    
                    # Ищем день
                    day_data = next((d for d in data.get("weather", []) if d.get("date") == target_date_str), None)
                    if not day_data and data.get("weather"):
                        day_data = data["weather"][0]
                    
                    if day_data:
                        # Ищем ближайший 3-часовой интервал (0, 300, 600, 900, 1200, 1500, 1800, 2100)
                        target_code = target_hour * 100
                        hourly_list = day_data.get("hourly", [])
                        closest_hour = min(hourly_list, key=lambda h: abs(int(h.get("time", "0")) - target_code)) if hourly_list else {}
                        
                        raw_desc = (closest_hour.get("weatherDesc", [{}])[0].get("value") or "Partly cloudy")
                        desc_ru, icon = _translate_weather(raw_desc)
                        temp_c = int(closest_hour.get("tempC", 14))
                        rain_chance = int(closest_hour.get("chanceofrain", 0))
                        is_rain = rain_chance >= 40 or "дождь" in desc_ru.lower() or "гроза" in desc_ru.lower()
                        
                        rain_note = f", вероятность осадков {rain_chance}%" if rain_chance > 20 else ", без осадков"
                        res = {
                            "temp_c": temp_c,
                            "feels_like_c": int(closest_hour.get("FeelsLikeC", temp_c)),
                            "description": desc_ru,
                            "icon": icon,
                            "precipitation_chance": rain_chance,
                            "is_rain": is_rain,
                            "summary": f"{'+' if temp_c > 0 else ''}{temp_c}°C, {desc_ru.lower()}{rain_note}",
                            "location": "Санкт-Петербург",
                        }
                        _CACHE[cache_key] = (now_ts, res)
                        return res

                # Текущие условия
                current = (data.get("current_condition") or [{}])[0]
                raw_desc = (current.get("weatherDesc") or [{}])[0].get("value") or "Partly cloudy"
                desc_ru, icon = _translate_weather(raw_desc)
                temp_c = int(current.get("temp_C", 14))
                feels_c = int(current.get("FeelsLikeC", temp_c))
                
                res = {
                    "temp_c": temp_c,
                    "feels_like_c": feels_c,
                    "description": desc_ru,
                    "icon": icon,
                    "precipitation_chance": 0,
                    "is_rain": "дождь" in desc_ru.lower(),
                    "summary": f"{'+' if temp_c > 0 else ''}{temp_c}°C, {desc_ru.lower()}",
                    "location": "Санкт-Петербург",
                }
                _CACHE[cache_key] = (now_ts, res)
                return res
    except Exception as exc:
        logger.debug("wttr.in weather fetch exception: %s", exc)

    fallback = _fallback_weather(target_time)
    _CACHE[cache_key] = (now_ts, fallback)
    return fallback


def get_forecast_summary_sync(lat: float, lon: float, target_time: datetime | None = None) -> str:
    """Синхронная функция быстрого получения строки погоды для карточки бота из кеша или fallback."""
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)
    hour_key = f"{target_time.strftime('%Y-%m-%d-%H')}" if target_time else "current"
    cache_key = f"{lat_r}:{lon_r}:{hour_key}"
    if cache_key in _CACHE:
        return _CACHE[cache_key][1]["summary"]
    fallback = _fallback_weather(target_time)
    return fallback["summary"]
