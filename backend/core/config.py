"""Настройки приложения. Все значения читаются из переменных окружения (или файла .env)."""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

WEBHOOK_SECRET_RE = re.compile(r"^[A-Za-z0-9-]{5,256}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # --- Приложение ---
    app_name: str = "MAX Стрит"
    log_level: str = "INFO"
    app_timezone: str = "Europe/Moscow"
    cors_origins: str = "https://fufuraziy.github.io,https://max-street.pages.dev,http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8000,*"

    # --- База данных ---
    # DATABASE_URL имеет приоритет; иначе URL собирается из POSTGRES_* (пароль экранируется).
    database_url: str = ""
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "maxstreet"
    postgres_password: str = "maxstreet"
    postgres_db: str = "maxstreet"

    # --- Тестовые данные ---
    seed_demo_data: bool = True
    slots_seed_days: int = 5

    # --- Аренда кортов и эскроу (mock-провайдеры) ---
    payment_mode: str = "mock"  # mock — тестовый СБП и mock-арендодатель, реальные деньги не списываются
    escrow_deadline_minutes: int = 120  # дедлайн сбора средств: за столько минут до начала слота
    escrow_watchdog_interval_seconds: int = 30
    booking_webhook_url: str = ""  # URL внешней системы арендодателя (если пусто — только mock-провайдер)
    booking_webhook_secret: str = ""  # подпись вебхука: X-MaxStreet-Signature: sha256=<hmac>
    booking_provider_name: str = "MAX Sport Booking (mock)"

    # --- MAX Bot API ---
    max_bot_token: str = ""
    max_api_base_url: str = "https://platform-api2.max.ru"
    max_bot_mode: str = "auto"  # auto | polling | webhook | disabled
    max_webhook_url: str = ""
    max_webhook_secret: str = ""
    max_use_open_app_button: bool = True
    miniapp_url: str = "https://fufuraziy.github.io/max_street"

    # --- Безопасность ---
    require_init_data: bool = False
    init_data_max_age_seconds: int = 86400
    admin_token: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            url = self.database_url
            for prefix in ("postgres://", "postgresql://"):
                if url.startswith(prefix):
                    return "postgresql+asyncpg://" + url[len(prefix):]
            return url
        return (
            f"postgresql+asyncpg://{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{quote_plus(self.postgres_db)}"
        )

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()] or ["*"]

    @property
    def bot_mode(self) -> str:
        """Итоговый режим бота: disabled | polling | webhook."""
        if not self.max_bot_token:
            return "disabled"
        mode = self.max_bot_mode.strip().lower()
        if mode == "auto":
            return "webhook" if self.max_webhook_url else "polling"
        return mode if mode in {"polling", "webhook", "disabled"} else "disabled"

    @property
    def webhook_secret_is_valid(self) -> bool:
        return not self.max_webhook_secret or bool(WEBHOOK_SECRET_RE.match(self.max_webhook_secret))

    @property
    def public_miniapp_url(self) -> str:
        return self.miniapp_url.rstrip("/")

    @property
    def mock_payments(self) -> bool:
        return self.payment_mode.strip().lower() == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
