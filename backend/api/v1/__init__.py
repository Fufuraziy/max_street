from fastapi import APIRouter

from api.v1 import bot_webhook, courts, defects, games, mock, weather

# Базовый роутер со всеми модулями (courts, games, defects, bot, mock, weather)
core_router = APIRouter()
core_router.include_router(courts.router)
core_router.include_router(games.router)
core_router.include_router(defects.router)
core_router.include_router(bot_webhook.router)
core_router.include_router(mock.router)
core_router.include_router(weather.router)

# Канонический префикс /api/v1
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(core_router)

# Алиас /api
api_prefix_router = APIRouter(prefix="/api")
api_prefix_router.include_router(core_router)

# Корневой алиас / (для прямых запросов /spots, /courts, /games и т.д.)
root_api_router = APIRouter(prefix="")
root_api_router.include_router(core_router)

# Для обратной совместимости
api_router = api_v1_router

__all__ = ["api_router", "api_v1_router", "api_prefix_router", "root_api_router", "core_router"]
