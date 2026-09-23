from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from core.config import settings
from services.max_bot import bot_service

router = APIRouter(prefix="/bot", tags=["Бот MAX"])


@router.post("/webhook", summary="Входящие события MAX Bot API")
async def max_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_max_bot_api_secret: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Принимает Update от MAX (`message_created`, `message_callback`, `bot_started`).

    Команды: /start, /help, /find [спорт], /my, /near, /map, свободный текст и геолокация.

    * `MAX_BOT_MODE=webhook`: сразу отвечаем 200 (MAX ждёт не дольше 30 с), а событие
      обрабатывается в фоне, и ответы уходят в MAX.
    * Остальные режимы: dry-run. Эндпоинт возвращает сформированные сообщения (`replies`),
      поэтому логику бота можно проверить обычным curl без токена.
    """
    if settings.max_webhook_secret and not hmac.compare_digest(
        x_max_bot_api_secret or "", settings.max_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Неверный секрет webhook")
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Ожидается JSON-объект Update") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ожидается JSON-объект Update")

    updates = [u for u in (payload["updates"] if isinstance(payload.get("updates"), list) else [payload]) if isinstance(u, dict)]

    if bot_service.mode == "webhook":
        for update in updates:
            background_tasks.add_task(bot_service.handle_update, update)
        return {"ok": True, "queued": len(updates)}

    replies: list[dict[str, Any]] = []
    for update in updates:
        replies.extend(await bot_service.handle_update(update, deliver=False))
    return {"ok": True, "delivered": False, "replies": replies}


@router.get("/info", summary="Сведения о боте (из GET /me)")
async def bot_info() -> dict[str, Any]:
    return bot_service.info()
