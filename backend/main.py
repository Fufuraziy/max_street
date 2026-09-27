"""MAX Стрит: интерактивная карта и матчмейкинг дворового спорта (FastAPI)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import BackgroundTasks, FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from api.v1 import api_prefix_router, api_v1_router, root_api_router
from core.config import settings
from core.database import SessionLocal, create_tables, engine, wait_for_db
from core.errors import DomainError
from services import escrow
from services.max_bot import bot_service
from services.seeder import run_seed

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("maxstreet")

FIELD_LABELS = {
    "title": "Название",
    "address": "Адрес",
    "sport_types": "Виды спорта",
    "sport_type": "Вид спорта",
    "surface_type": "Покрытие",
    "latitude": "Широта",
    "longitude": "Долгота",
    "start_time": "Время начала",
    "required_players": "Количество игроков",
    "comment": "Комментарий",
    "description": "Описание",
    "creator_name": "Имя",
    "user_name": "Имя",
    "creator_max_id": "ID пользователя",
    "user_max_id": "ID пользователя",
    "defect_type": "Тип проблемы",
    "court_id": "Площадка",
    "slot_id": "Слот аренды",
    "amount": "Сумма",
}


def _validation_message(error: dict[str, Any]) -> str:
    field = next(
        (str(part) for part in reversed(error.get("loc", ())) if isinstance(part, str) and part not in {"body", "query", "path"}),
        "",
    )
    ctx = error.get("ctx") or {}
    messages = {
        "missing": "обязательное поле",
        "string_too_short": f"минимум {ctx.get('min_length')} симв.",
        "string_too_long": f"максимум {ctx.get('max_length')} симв.",
        "too_short": f"выберите хотя бы {ctx.get('min_length')}",
        "too_long": f"не больше {ctx.get('max_length')} значений",
        "greater_than_equal": f"не меньше {ctx.get('ge')}",
        "greater_than": f"больше {ctx.get('gt')}",
        "less_than_equal": f"не больше {ctx.get('le')}",
        "enum": "недопустимое значение",
        "datetime_from_date_parsing": "неверный формат даты",
        "datetime_parsing": "неверный формат даты",
        "json_invalid": "некорректный JSON",
    }
    if error.get("type") == "value_error":
        message = str(ctx.get("error") or error.get("msg", ""))
    else:
        message = messages.get(error.get("type", ""), error.get("msg", "некорректное значение"))
    label = FIELD_LABELS.get(field, field)
    return f"{label}: {message}" if label else message


async def escrow_watchdog() -> None:
    """Фоновая проверка дедлайнов эскроу-сборов: не набравшим сумму — автоматический возврат средств."""
    while True:
        try:
            async with SessionLocal() as session:
                expired = await escrow.expire_overdue(session)
            for game_id, refunds in expired:
                await bot_service.notify_refund(game_id, refunds, "deadline")
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - сторож не должен падать
            logger.exception("Ошибка проверки дедлайнов эскроу")
        await asyncio.sleep(settings.escrow_watchdog_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await wait_for_db()
    await create_tables()
    async with SessionLocal() as session:
        await run_seed(session)
    await bot_service.start()
    watchdog = asyncio.create_task(escrow_watchdog(), name="escrow-watchdog")
    logger.info("MAX Стрит запущен, режим бота: %s, платежи: %s", bot_service.mode, settings.payment_mode)
    yield
    watchdog.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await watchdog
    await bot_service.stop()
    await engine.dispose()


app = FastAPI(
    title="MAX Стрит API",
    version="1.0.0",
    description=(
        "Интерактивная карта спортплощадок, лобби для командных игр и заявки о поломках. "
        "Бэкенд чат-бота и мини-приложения MAX."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    detail = "; ".join(dict.fromkeys(_validation_message(error) for error in errors)) or "Некорректный запрос"
    return JSONResponse(status_code=422, content={"detail": detail, "errors": jsonable_encoder(errors)})


# Регистрация маршрутов: канонические /api/v1, алиасы /api и корневые /
app.include_router(api_v1_router)
app.include_router(api_prefix_router)
app.include_router(root_api_router)


@app.post("/webhook", tags=["Бот MAX"], summary="Входящие события MAX Bot API (корневой эндпоинт)")
async def root_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_max_bot_api_secret: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Корневой алиас вебхука MAX Bot API."""
    from api.v1.bot_webhook import max_webhook
    return await max_webhook(request, background_tasks, x_max_bot_api_secret)


@app.get("/health", tags=["Служебное"], summary="Проверка работоспособности (root)")
@app.get("/api/health", tags=["Служебное"], summary="Проверка работоспособности (/api)")
@app.get("/api/v1/health", tags=["Служебное"], summary="Проверка работоспособности (/api/v1)")
async def health() -> JSONResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Healthcheck: БД недоступна: %s", exc)
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})
    return JSONResponse({"status": "ok", "database": "ok", "bot_mode": bot_service.mode})


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/api/docs")

