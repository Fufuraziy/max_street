"""Общие зависимости REST API: сессия БД, идентификация пользователя, доступ администратора."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_session
from core.security import Identity, identity_from_max_user, validate_init_data

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_init_identity(x_max_init_data: Annotated[str | None, Header()] = None) -> Identity | None:
    """Пользователь из подписанного initData мини-приложения (заголовок X-Max-Init-Data).

    Если подпись верна, id и имя берутся из initData, а не из тела запроса.
    """
    if not x_max_init_data or not settings.max_bot_token:
        return None
    data = validate_init_data(x_max_init_data, settings.max_bot_token, settings.init_data_max_age_seconds)
    user = (data or {}).get("user")
    if not isinstance(user, dict):
        if settings.require_init_data:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Подпись данных MAX недействительна, перезапустите мини-приложение")
        return None
    return identity_from_max_user(user, verified=True)


InitIdentityDep = Annotated[Identity | None, Depends(get_init_identity)]


def resolve_identity(verified: Identity | None, max_user_id: str, name: str, username: str | None = None) -> Identity:
    if verified is not None:
        return verified
    if settings.require_init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Откройте мини-приложение внутри MAX, чтобы выполнить действие")
    return Identity(max_user_id=max_user_id, name=name, username=username)


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    if not settings.admin_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Управление заявками отключено: задайте ADMIN_TOKEN")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный X-Admin-Token")
