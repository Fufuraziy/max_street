from fastapi import APIRouter

from api.v1 import bot_webhook, courts, defects, games, mock

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(courts.router)
api_router.include_router(games.router)
api_router.include_router(defects.router)
api_router.include_router(bot_webhook.router)
api_router.include_router(mock.router)

__all__ = ["api_router"]
