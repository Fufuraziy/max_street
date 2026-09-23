"""Служебные эндпоинты mock-интеграций (доступны только при PAYMENT_MODE=mock).

По регламенту хакатона оплата и бронирование эмулируются. Эти эндпоинты помогают жюри
проверить сценарии, которые иначе пришлось бы ждать: наступление дедлайна сбора (возврат
средств) и получение брони внешней системой арендодателя.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import SessionDep
from core.config import settings
from schemas.game import GameWithCourt
from services import escrow
from services.max_bot import bot_service
from services.mock_booking_provider import booking_provider


def require_mock_mode() -> None:
    if not settings.mock_payments:
        raise HTTPException(status_code=404, detail="Mock-интеграции отключены (PAYMENT_MODE != mock)")


router = APIRouter(prefix="/mock", tags=["Mock-интеграции"], dependencies=[Depends(require_mock_mode)])


@router.post("/escrow/{game_id}/expire", summary="Симулировать дедлайн сбора (возврат средств)")
async def expire_escrow(game_id: int, session: SessionDep, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Дедлайн наступает немедленно: все взносы возвращаются участникам, лобби отменяется, слот освобождается."""
    game, refunds = await escrow.force_expire(session, game_id)
    background_tasks.add_task(bot_service.notify_refund, game.id, refunds, "deadline")
    return {
        "game": GameWithCourt.model_validate(game).model_dump(mode="json"),
        "refunds": [{"user_max_id": r.user_max_id, "user_name": r.user_name, "amount": float(r.amount)} for r in refunds],
        "message": f"Сбор отменён, возвратов: {len(refunds)}",
    }


@router.get("/provider/bookings", summary="Брони, полученные mock-арендодателем")
async def provider_bookings() -> dict[str, Any]:
    """Вебхуки о выкупе слотов, которые «получила» внешняя система арендодателя (последние 200)."""
    return {
        "provider": booking_provider.name,
        "webhook_url": settings.booking_webhook_url or None,
        "bookings": list(booking_provider.received),
    }
