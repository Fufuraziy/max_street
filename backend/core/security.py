"""Идентификация пользователя и проверка подписи initData мини-приложения MAX.

Алгоритм (документация MAX, раздел «Валидация данных»):
    secret_key = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
    data_check_string = "\\n".join(f"{k}={v}" for k, v in sorted(params without hash))
    hash == hex(HMAC_SHA256(key=secret_key, msg=data_check_string))
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


@dataclass(frozen=True, slots=True)
class Identity:
    max_user_id: str
    name: str
    username: str | None = None
    verified: bool = False

    @property
    def is_max_user(self) -> bool:
        """Настоящий пользователь MAX (числовой id) — ему можно писать от имени бота."""
        return self.max_user_id.isdigit()


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 0) -> dict[str, Any] | None:
    """Возвращает распарсенные данные запуска, если подпись верна, иначе None."""
    if not init_data or not bot_token:
        return None
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None

    received_hash = params.pop("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash.lower()):
        return None

    if max_age_seconds > 0:
        try:
            auth_date = int(params.get("auth_date", "0"))
        except ValueError:
            return None
        # auth_date может приходить в секундах или миллисекундах
        if auth_date > 10**12:
            auth_date //= 1000
        if time.time() - auth_date > max_age_seconds:
            return None

    parsed: dict[str, Any] = dict(params)
    for key in ("user", "chat"):
        if key in parsed:
            try:
                parsed[key] = json.loads(parsed[key])
            except (TypeError, ValueError):
                parsed[key] = None
    return parsed


def identity_from_max_user(user: dict[str, Any], *, verified: bool) -> Identity | None:
    """Строит Identity из объекта пользователя MAX (Bot API или initData)."""
    user_id = user.get("user_id", user.get("id"))
    if user_id is None:
        return None
    full_name = " ".join(part for part in (user.get("first_name"), user.get("last_name")) if part)
    name = full_name or user.get("name") or user.get("username") or "Игрок MAX"
    return Identity(
        max_user_id=str(user_id),
        name=str(name)[:64],
        username=user.get("username") or None,
        verified=verified,
    )
