"""Интеграция с MAX Bot API (по умолчанию https://platform-api2.max.ru).

Используемые методы:
    GET  /me             — имя и username бота (из них строится deep link на мини-приложение);
    POST /messages       — ответы на команды и уведомления игрокам;
    POST /answers        — ответ на нажатие callback-кнопки (сообщение редактируется «на месте»);
    GET  /updates        — long polling: бот работает без публичного HTTPS-адреса;
    GET/POST /subscriptions — webhook для продакшена.

Токен передаётся только в заголовке «Authorization: <token>». Без токена сервис работает
в dry-run режиме: webhook возвращает сформированные ответы, уведомления пишутся в лог.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import html
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, settings
from core.database import SessionLocal
from core.errors import DomainError
from core.security import Identity, identity_from_max_user
from core.timeutils import human_datetime, short_datetime
from models import Game
from models.enums import (
    DefectStatus,
    GAME_STATUS_LABELS,
    GameStatus,
    SURFACE_LABELS,
    SportType,
    detect_sport,
    sport_emoji,
    sport_label,
)
from services import courts as court_service
from services import games as game_service

logger = logging.getLogger(__name__)

UPDATE_TYPES = ["message_created", "message_callback", "bot_started"]
MAX_TEXT_LENGTH = 4000
POLL_TIMEOUT_SECONDS = 30

Button = dict[str, Any]
Action = dict[str, Any]


# ---------------------------------------------------------------------------
# Вспомогательные функции форматирования
# ---------------------------------------------------------------------------

def esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def plural(number: int, forms: tuple[str, str, str]) -> str:
    n = abs(number) % 100
    if 10 < n < 20:
        return forms[2]
    if n % 10 == 1:
        return forms[0]
    if 2 <= n % 10 <= 4:
        return forms[1]
    return forms[2]


def format_label(sport: str, players: int) -> str:
    """6 игроков в баскетболе → «3×3»; для воркаута — просто размер группы."""
    if sport == SportType.WORKOUT or players % 2:
        return f"{players} {plural(players, ('участник', 'участника', 'участников'))}"
    return f"{players // 2}×{players // 2}"


def format_distance(meters: float) -> str:
    if meters < 1000:
        return f"{int(round(meters / 10) * 10)} м"
    return f"{meters / 1000:.1f} км".replace(".", ",")


def route_url(lat: float, lon: float) -> str:
    return f"https://yandex.ru/maps/?rtext=~{lat:.6f},{lon:.6f}&rtt=pd"


def cb(text: str, payload: str) -> Button:
    return {"type": "callback", "text": text, "payload": payload}


def link(text: str, url: str) -> Button:
    return {"type": "link", "text": text, "url": url}


def geo(text: str) -> Button:
    return {"type": "request_geo_location", "text": text}


def parse_ref(payload: str, prefix: str) -> int | None:
    """«court_12» → 12."""
    head, _, tail = payload.partition("_")
    return int(tail) if head == prefix and tail.isdigit() else None


@dataclass(slots=True)
class View:
    """Текст + inline-клавиатура. None-кнопки и пустые ряды отбрасываются."""

    text: str
    buttons: list[list[Button | None]] = field(default_factory=list)

    def body(self, *, replace_keyboard: bool = False) -> dict[str, Any]:
        body: dict[str, Any] = {"text": self.text[:MAX_TEXT_LENGTH], "format": "html"}
        rows = [[button for button in row if button] for row in self.buttons]
        rows = [row for row in rows if row]
        if rows:
            body["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": rows}}]
        elif replace_keyboard:
            body["attachments"] = []
        return body


# ---------------------------------------------------------------------------
# HTTP-клиент MAX Bot API
# ---------------------------------------------------------------------------

class MaxApiError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"MAX API {status}: {body[:300]}")
        self.status = status
        self.body = body


class MaxApiClient:
    def __init__(self, token: str, base_url: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": token},
            timeout=httpx.Timeout(15.0, connect=10.0),
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> dict[str, Any]:
        extra: dict[str, Any] = {"timeout": timeout} if timeout is not None else {}
        response = await self._client.request(method, path, params=params, json=json, **extra)
        if response.status_code >= 400:
            raise MaxApiError(response.status_code, response.text)
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {"result": data}

    async def get_me(self) -> dict[str, Any]:
        return await self.request("GET", "/me")

    async def send_message(
        self, body: dict[str, Any], *, chat_id: int | None = None, user_id: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        elif user_id is not None:
            params["user_id"] = user_id
        return await self.request("POST", "/messages", params=params, json=body)

    async def answer_callback(self, callback_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/answers", params={"callback_id": callback_id}, json=body)

    async def get_updates(self, *, marker: int | None, timeout: int, types: list[str]) -> dict[str, Any]:
        params: dict[str, Any] = {"timeout": timeout, "limit": 100, "types": ",".join(types)}
        if marker is not None:
            params["marker"] = marker
        return await self.request(
            "GET", "/updates", params=params, timeout=httpx.Timeout(timeout + 15.0, connect=10.0)
        )

    async def get_subscriptions(self) -> dict[str, Any]:
        return await self.request("GET", "/subscriptions")

    async def subscribe(self, url: str, update_types: list[str], secret: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {"url": url, "update_types": update_types}
        if secret:
            body["secret"] = secret
        return await self.request("POST", "/subscriptions", json=body)

    async def aclose(self) -> None:
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Сервис бота
# ---------------------------------------------------------------------------

class MaxBotService:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.mode = cfg.bot_mode
        self.client: MaxApiClient | None = None
        self.bot_info: dict[str, Any] | None = None
        self._open_app_enabled = cfg.max_use_open_app_button
        self._polling_task: asyncio.Task[None] | None = None

    # --- жизненный цикл -----------------------------------------------------

    async def start(self) -> None:
        if not self.cfg.max_bot_token:
            logger.info("MAX_BOT_TOKEN не задан — бот в dry-run режиме: webhook возвращает ответы, уведомления пишутся в лог")
            return
        self.client = MaxApiClient(self.cfg.max_bot_token, self.cfg.max_api_base_url)
        await self._load_bot_info()
        if self.mode == "webhook":
            await self._setup_webhook()
        elif self.mode == "polling":
            await self._warn_if_webhook_active()
            self._polling_task = asyncio.create_task(self._poll_forever(), name="max-bot-polling")
        else:
            logger.info("MAX_BOT_MODE=disabled — входящие события не обрабатываются")

    async def stop(self) -> None:
        if self._polling_task is not None:
            self._polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._polling_task
        if self.client is not None:
            await self.client.aclose()

    async def _load_bot_info(self) -> None:
        assert self.client is not None
        try:
            self.bot_info = await self.client.get_me()
            logger.info("Бот MAX подключён: %s (@%s, id=%s)", self.bot_name, self.bot_username, self.bot_id)
        except (MaxApiError, httpx.HTTPError) as exc:
            logger.error("GET /me завершился ошибкой: %s", exc)

    async def _setup_webhook(self) -> None:
        assert self.client is not None
        url = self.cfg.max_webhook_url.strip()
        if not url.startswith("https://"):
            logger.error("MAX_WEBHOOK_URL должен начинаться с https:// (MAX принимает только HTTPS на 443 порту)")
            return
        if not self.cfg.webhook_secret_is_valid:
            logger.error("MAX_WEBHOOK_SECRET должен состоять из 5–256 символов A-Z, a-z, 0-9 и «-»")
            return
        if not self.cfg.max_webhook_secret:
            logger.warning("MAX_WEBHOOK_SECRET не задан — рекомендуем задать секрет для проверки входящих запросов")
        try:
            result = await self.client.subscribe(url, UPDATE_TYPES, self.cfg.max_webhook_secret or None)
            if result.get("success", True):
                logger.info("Webhook MAX зарегистрирован: %s", url)
            else:
                logger.error("MAX отклонил подписку на webhook: %s", result.get("message"))
        except (MaxApiError, httpx.HTTPError) as exc:
            logger.error("Не удалось подписаться на webhook: %s", exc)

    async def _warn_if_webhook_active(self) -> None:
        assert self.client is not None
        try:
            data = await self.client.get_subscriptions()
        except (MaxApiError, httpx.HTTPError) as exc:
            logger.debug("GET /subscriptions: %s", exc)
            return
        urls = [item.get("url", "?") for item in data.get("subscriptions") or []]
        if urls:
            logger.warning(
                "У бота активны webhook-подписки (%s): пока они есть, long polling не получает события. "
                "Удалите подписку (DELETE /subscriptions?url=...) или включите MAX_BOT_MODE=webhook.",
                ", ".join(urls),
            )

    async def _poll_forever(self) -> None:
        assert self.client is not None
        marker: int | None = None
        backoff = 1.0
        logger.info("MAX long polling запущен")
        while True:
            try:
                data = await self.client.get_updates(marker=marker, timeout=POLL_TIMEOUT_SECONDS, types=UPDATE_TYPES)
                marker = data.get("marker", marker)
                for update in data.get("updates") or []:
                    await self.handle_update(update)
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except MaxApiError as exc:
                if exc.status == 401:
                    logger.error("MAX отклонил токен (401) — long polling остановлен, проверьте MAX_BOT_TOKEN")
                    return
                logger.warning("Ошибка long polling: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("MAX API недоступен (%s), повтор через %.0f с", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    # --- сведения о боте и ссылки -------------------------------------------------

    @property
    def bot_name(self) -> str | None:
        info = self.bot_info or {}
        return info.get("first_name") or info.get("name")

    @property
    def bot_username(self) -> str | None:
        return (self.bot_info or {}).get("username")

    @property
    def bot_id(self) -> int | None:
        return (self.bot_info or {}).get("user_id")

    def info(self) -> dict[str, Any]:
        return {
            "enabled": self.client is not None,
            "connected": self.bot_info is not None,
            "mode": self.mode,
            "name": self.bot_name,
            "username": self.bot_username,
            "deep_link": self.deep_link(),
            "miniapp_url": self.cfg.public_miniapp_url,
        }

    def deep_link(self, payload: str | None = None) -> str | None:
        """Ссылка, открывающая мини-приложение бота: https://max.ru/<botName>?startapp=<payload>."""
        if not self.bot_username:
            return None
        return f"https://max.ru/{self.bot_username}?startapp" + (f"={payload}" if payload else "")

    def web_link(self, payload: str | None = None) -> str:
        court_id = parse_ref(payload or "", "court")
        base = self.cfg.public_miniapp_url
        return f"{base}/?court={court_id}" if court_id else f"{base}/"

    def app_button(self, text: str, payload: str | None = None) -> Button | None:
        """Кнопка запуска мини-приложения: open_app, если известен бот, иначе ссылка."""
        if self._open_app_enabled and self.bot_username:
            button: Button = {"type": "open_app", "text": text, "web_app": self.bot_username}
            if self.bot_id:
                button["contact_id"] = self.bot_id
            if payload:
                button["payload"] = payload
            return button
        url = self.deep_link(payload)
        if url is None:
            url = self.web_link(payload)
            # MAX не принимает ссылки вида http://localhost — такую кнопку не отправляем.
            if self.client is not None and not url.startswith("https://"):
                return None
        return link(text, url)

    # --- обработка входящих событий -------------------------------------------------

    async def handle_update(self, update: dict[str, Any], *, deliver: bool = True) -> list[Action]:
        """Обрабатывает Update из webhook или long polling. Возвращает список исходящих действий."""
        try:
            actions = await self._dispatch(update)
        except Exception:
            logger.exception("Ошибка обработки события %s", update.get("update_type"))
            return []
        if deliver:
            await self.deliver_all(actions)
        return actions

    async def _dispatch(self, update: dict[str, Any]) -> list[Action]:
        update_type = update.get("update_type")
        async with SessionLocal() as session:
            if update_type == "message_created":
                return await self._on_message(session, update)
            if update_type == "message_callback":
                return await self._on_callback(session, update)
            if update_type == "bot_started":
                return await self._on_bot_started(session, update)
        return []

    async def _on_message(self, session: AsyncSession, update: dict[str, Any]) -> list[Action]:
        message = update.get("message") or {}
        sender = message.get("sender") or {}
        if sender.get("is_bot"):
            return []
        identity = identity_from_max_user(sender, verified=True)
        if identity is None:
            return []
        recipient = message.get("recipient") or {}
        target = {"chat_id": recipient["chat_id"]} if recipient.get("chat_id") is not None else {"user_id": int(identity.max_user_id)}
        body = message.get("body") or {}
        text = (body.get("text") or "").strip()

        for attachment in body.get("attachments") or []:
            if attachment.get("type") == "location":
                lat = attachment.get("latitude", (attachment.get("payload") or {}).get("latitude"))
                lon = attachment.get("longitude", (attachment.get("payload") or {}).get("longitude"))
                if lat is not None and lon is not None:
                    return [self._send(target, await self._nearby_view(session, float(lat), float(lon)))]

        command, _, argument = text.partition(" ")
        command = command.lower().split("@", 1)[0]
        argument = argument.strip()

        if command in {"/start", "start", "старт", "начать", "привет", "меню", "/menu"}:
            view = self._welcome_view(identity)
        elif command in {"/help", "help", "помощь", "?"}:
            view = self._help_view()
        elif command in {"/find", "find", "найти", "сборы", "игры", "/games"}:
            view = await self._games_view(session, detect_sport(argument) if argument else None)
        elif command in {"/my", "мои"}:
            view = await self._my_games_view(session, identity)
        elif command in {"/near", "рядом"}:
            view = self._ask_location_view()
        elif command in {"/map", "карта"}:
            view = self._map_view()
        elif sport := detect_sport(text):
            view = await self._games_view(session, sport)
        else:
            view = self._fallback_view()
        return [self._send(target, view)]

    async def _on_bot_started(self, session: AsyncSession, update: dict[str, Any]) -> list[Action]:
        identity = identity_from_max_user(update.get("user") or {}, verified=True)
        if identity is None:
            return []
        chat_id = update.get("chat_id")
        target = {"chat_id": chat_id} if chat_id is not None else {"user_id": int(identity.max_user_id)}
        actions = [self._send(target, self._welcome_view(identity))]
        court_id = parse_ref((update.get("payload") or "").strip(), "court")
        if court_id:
            try:
                actions.append(self._send(target, await self._court_view(session, court_id)))
            except DomainError:
                pass
        return actions

    async def _on_callback(self, session: AsyncSession, update: dict[str, Any]) -> list[Action]:
        callback = update.get("callback") or {}
        callback_id = callback.get("callback_id")
        identity = identity_from_max_user(callback.get("user") or {}, verified=True)
        if not callback_id or identity is None:
            return []

        action, _, argument = (callback.get("payload") or "").strip().partition(":")
        extra: list[Action] = []
        try:
            if action == "find":
                view = await self._games_view(session, argument or None)
            elif action == "my":
                view = await self._my_games_view(session, identity)
            elif action == "court":
                view = await self._court_view(session, int(argument))
            elif action == "join":
                joined = await game_service.join_game(session, int(argument), identity)
                view = self._join_result_view(joined)
                if joined.confirmed:
                    self._log_quorum(joined.game)
                if joined.joined:
                    extra = (
                        self._confirmed_actions(joined.game, exclude=identity.max_user_id)
                        if joined.confirmed
                        else self._joined_actions(joined.game, identity)
                    )
            elif action == "leave":
                left = await game_service.leave_game(session, int(argument), identity)
                view = self._leave_result_view(left)
                extra = self._left_actions(left, identity)
            elif action == "menu":
                view = self._welcome_view(identity)
            else:
                view = self._help_view()
        except DomainError as exc:
            view = View(
                f"⚠️ {esc(exc.message)}",
                [[cb("🔥 К списку сборов", "find")], [self.app_button("🗺 Открыть карту")]],
            )
        except ValueError:
            view = self._help_view()
        return [self._answer(callback_id, view), *extra]

    # --- уведомления (вызываются из REST API в фоне) ----------------------------------

    async def notify_after_join(self, game_id: int, joiner: Identity, confirmed: bool) -> None:
        async with SessionLocal() as session:
            game = await game_service.get_game(session, game_id)
        if confirmed:
            self._log_quorum(game)
        actions = self._confirmed_actions(game) if confirmed else self._joined_actions(game, joiner)
        await self.deliver_all(actions)

    @staticmethod
    def _log_quorum(game: Game) -> None:
        recipients = sum(1 for p in game.participants if p.user_max_id.isdigit())
        logger.info(
            "[quorum] Состав собран: сбор #%s (%s, %s/%s, %s). Уведомления в MAX: %s, без MAX id (гости/демо): %s",
            game.id,
            sport_label(game.sport_type),
            game.current_players,
            game.required_players,
            game.court.title,
            recipients,
            len(game.participants) - recipients,
        )

    async def notify_after_leave(self, result: game_service.LeaveResult, leaver: Identity) -> None:
        await self.deliver_all(self._left_actions(result, leaver))

    def _confirmed_actions(self, game: Game, exclude: str | None = None) -> list[Action]:
        view = View(
            "✅ <b>Состав собран!</b>\n\n"
            + self._game_card(game)
            + "\n\nДо встречи на площадке! Если планы изменятся, выйдите из сбора, чтобы освободить место.",
            [
                [self.app_button("📍 Открыть площадку", f"court_{game.court_id}")],
                [link("🧭 Маршрут", route_url(game.court.latitude, game.court.longitude)), cb("🙋 Мои игры", "my")],
            ],
        )
        return [
            self._send_to_user(participant.user_max_id, view)
            for participant in game.participants
            if participant.user_max_id.isdigit() and participant.user_max_id != exclude
        ]

    def _joined_actions(self, game: Game, joiner: Identity) -> list[Action]:
        if game.creator_max_id == joiner.max_user_id or not game.creator_max_id.isdigit():
            return []
        view = View(
            f"➕ В вашем сборе новый игрок: <b>{esc(joiner.name)}</b>\n\n" + self._game_card(game),
            [[self.app_button("📍 Открыть площадку", f"court_{game.court_id}")]],
        )
        return [self._send_to_user(game.creator_max_id, view)]

    def _left_actions(self, result: game_service.LeaveResult, leaver: Identity) -> list[Action]:
        game = result.game
        if result.cancelled or game.creator_max_id == leaver.max_user_id or not game.creator_max_id.isdigit():
            return []
        if result.new_creator is not None:
            head = f"👑 Организатор вышел из сбора — теперь организатор вы. Из сбора вышел: <b>{esc(leaver.name)}</b>"
        else:
            head = f"➖ Из вашего сбора вышел игрок: <b>{esc(leaver.name)}</b>"
        if result.reopened:
            head += "\nНабор снова открыт."
        view = View(head + "\n\n" + self._game_card(game), [[self.app_button("📍 Открыть площадку", f"court_{game.court_id}")]])
        return [self._send_to_user(game.creator_max_id, view)]

    # --- экраны бота ----------------------------------------------------------

    def _sport_filter_row(self) -> list[Button | None]:
        return [cb(sport_emoji(sport), f"find:{sport.value}") for sport in SportType]

    def _welcome_view(self, identity: Identity) -> View:
        first_name = esc(identity.name.split()[0]) if identity.name.strip() else "друг"
        text = (
            f"👋 Привет, {first_name}!\n\n"
            "<b>MAX Стрит</b> — карта дворовых спортплощадок и сборы на игры.\n\n"
            "🗺 Площадки рядом: покрытие, свет и кто сегодня играет\n"
            "👥 Сборы на 3×3, 5×5, волейбол или теннис. Когда состав соберётся, бот пришлёт уведомление\n"
            "🛠 Сломано кольцо или яма в покрытии? Заявка уйдёт в районные службы\n\n"
            "/find — ближайшие сборы · /my — мои игры · /near — площадки рядом · /help — помощь"
        )
        return View(
            text,
            [
                [self.app_button("🗺 Открыть карту площадок")],
                [cb("🔥 Ближайшие сборы", "find"), cb("🙋 Мои игры", "my")],
                [geo("📍 Площадки рядом со мной")],
            ],
        )

    def _help_view(self) -> View:
        text = (
            "ℹ️ <b>Как пользоваться MAX Стрит</b>\n\n"
            "/find — ближайшие сборы\n"
            "/find баскетбол — сборы по виду спорта (баскетбол, футбол, волейбол, теннис, воркаут)\n"
            "/my — игры, в которых вы участвуете\n"
            "/near — площадки рядом с вами (нужна геолокация)\n"
            "/map — открыть карту в мини-приложении\n\n"
            "Можно написать и обычным текстом, например «хочу в футбол»: бот подберёт сборы.\n"
            "В мини-приложении создаются свои сборы и отправляются заявки о поломках на площадках."
        )
        return View(text, [[self.app_button("🗺 Открыть карту")], [cb("🔥 Ближайшие сборы", "find")]])

    def _map_view(self) -> View:
        return View(
            "🗺 Все площадки, сборы и заявки о поломках есть на карте в мини-приложении.",
            [[self.app_button("🗺 Открыть карту площадок")]],
        )

    def _ask_location_view(self) -> View:
        return View(
            "📍 Пришлите геолокацию, и я покажу ближайшие площадки и сегодняшние сборы.",
            [[geo("📍 Отправить геолокацию")], [self.app_button("🗺 Открыть карту")]],
        )

    def _fallback_view(self) -> View:
        return View(
            "🤔 Не понял запрос. Напишите вид спорта, например «баскетбол», или воспользуйтесь кнопками ниже.",
            [[self.app_button("🗺 Открыть карту")], [cb("🔥 Ближайшие сборы", "find")], self._sport_filter_row()],
        )

    def _game_card(self, game: Game) -> str:
        names = ", ".join(esc(p.user_name) for p in game.participants) or "—"
        lines = [
            f"{sport_emoji(game.sport_type)} <b>{esc(sport_label(game.sport_type))} · {format_label(game.sport_type, game.required_players)}</b>",
            f"🕖 {human_datetime(game.start_time)}",
            f"📍 {esc(game.court.title)}",
            f"      {esc(game.court.address)}",
            f"👥 {game.current_players}/{game.required_players} · {GAME_STATUS_LABELS.get(game.status, game.status)}",
            f"Игроки: {names}",
        ]
        if game.comment:
            lines.append(f"💬 «{esc(game.comment)}»")
        return "\n".join(lines)

    def _game_line(self, index: int, game: Game) -> str:
        spots = game.spots_left
        status = (
            f"свободно {spots} {plural(spots, ('место', 'места', 'мест'))}"
            if game.status == GameStatus.RECRUITING and spots
            else GAME_STATUS_LABELS.get(game.status, game.status).lower()
        )
        line = (
            f"{index}. {sport_emoji(game.sport_type)} <b>{esc(sport_label(game.sport_type))} · "
            f"{format_label(game.sport_type, game.required_players)}</b>, {human_datetime(game.start_time)}\n"
            f"      📍 {esc(game.court.title)}\n"
            f"      👥 {game.current_players}/{game.required_players} · {status}"
        )
        if game.comment:
            line += f"\n      💬 {esc(game.comment[:120])}"
        return line

    async def _games_view(self, session: AsyncSession, sport: str | None) -> View:
        if sport and sport not in {s.value for s in SportType}:
            sport = None
        games = await game_service.list_games(session, sport_type=sport, limit=6)
        title = (
            f"{sport_emoji(sport)} <b>Сборы: {esc(sport_label(sport).lower())}</b>" if sport else "🔥 <b>Ближайшие сборы</b>"
        )
        if not games:
            return View(
                f"{title}\n\nПока никто не собирается. Создайте свой сбор на карте, а бот сообщит, когда наберётся команда.",
                [
                    [self.app_button("➕ Создать сбор на карте")],
                    self._sport_filter_row(),
                    [cb("🔄 Обновить", f"find:{sport or ''}")],
                ],
            )
        blocks = [title]
        buttons: list[list[Button | None]] = []
        for index, game in enumerate(games, 1):
            blocks.append(self._game_line(index, game))
            if game.status == GameStatus.RECRUITING and game.spots_left:
                buttons.append(
                    [cb(f"➕ {index}. {sport_emoji(game.sport_type)} {short_datetime(game.start_time)} · "
                        f"{game.current_players}/{game.required_players}", f"join:{game.id}")]
                )
            else:
                buttons.append([cb(f"ℹ️ {index}. {game.court.title[:40]}", f"court:{game.court_id}")])
        buttons.append(self._sport_filter_row())
        buttons.append([self.app_button("🗺 Все площадки на карте"), cb("🔄 Обновить", f"find:{sport or ''}")])
        return View("\n\n".join(blocks), buttons)

    async def _my_games_view(self, session: AsyncSession, identity: Identity) -> View:
        games = await game_service.list_games(session, user_max_id=identity.max_user_id, limit=10)
        if not games:
            return View(
                "🙋 У вас пока нет активных игр.\nЗагляните в /find или создайте свой сбор на карте.",
                [[cb("🔥 Ближайшие сборы", "find")], [self.app_button("🗺 Открыть карту")]],
            )
        blocks = ["🙋 <b>Мои игры</b>"]
        buttons: list[list[Button | None]] = []
        for index, game in enumerate(games, 1):
            line = self._game_line(index, game)
            if game.creator_max_id == identity.max_user_id:
                line += "\n      👑 вы организатор"
            blocks.append(line)
            buttons.append(
                [
                    cb(f"↩️ Выйти: {sport_emoji(game.sport_type)} {short_datetime(game.start_time)}", f"leave:{game.id}"),
                    cb("ℹ️ Площадка", f"court:{game.court_id}"),
                ]
            )
        buttons.append([self.app_button("🗺 Открыть карту")])
        return View("\n\n".join(blocks), buttons)

    async def _court_view(self, session: AsyncSession, court_id: int) -> View:
        details = await court_service.get_court_details(session, court_id)
        court = details.court
        sports = ", ".join(f"{sport_emoji(s)} {sport_label(s)}" for s in court.sport_types)
        lines = [
            f"🏟 <b>{esc(court.title)}</b>",
            f"📍 {esc(court.address)}",
            sports,
            f"Покрытие: {SURFACE_LABELS.get(court.surface_type, court.surface_type)} · "
            f"освещение: {'есть' if court.has_lighting else 'нет'} · ⭐ {court.rating:.1f}",
        ]
        if court.description:
            lines += ["", esc(court.description)]
        open_defects = [d for d in details.defects if d.status != DefectStatus.RESOLVED]
        if open_defects:
            lines += ["", f"🛠 Открытых заявок о поломках: {len(open_defects)}"]
        lines.append("")
        buttons: list[list[Button | None]] = []
        if details.games:
            lines.append("<b>Сборы:</b>")
            for game in details.games[:6]:
                lines.append(
                    f"• {sport_emoji(game.sport_type)} {human_datetime(game.start_time)}: "
                    f"{game.current_players}/{game.required_players}, "
                    f"{GAME_STATUS_LABELS.get(game.status, game.status).lower()}"
                )
                if game.status == GameStatus.RECRUITING and game.spots_left:
                    buttons.append(
                        [cb(f"➕ Вступить: {sport_emoji(game.sport_type)} {short_datetime(game.start_time)} · "
                            f"{game.current_players}/{game.required_players}", f"join:{game.id}")]
                    )
        else:
            lines.append("Сборов пока нет. Создайте первый в мини-приложении.")
        buttons.append([self.app_button("🗺 Открыть в мини-приложении", f"court_{court.id}")])
        buttons.append([link("🧭 Маршрут", route_url(court.latitude, court.longitude)), cb("🔥 Все сборы", "find")])
        return View("\n".join(lines), buttons)

    async def _nearby_view(self, session: AsyncSession, lat: float, lon: float) -> View:
        items = await court_service.nearest_courts(session, lat, lon, limit=5)
        if not items:
            return View(
                "😔 В радиусе 25 км площадок пока нет. Добавьте свою через мини-приложение.",
                [[self.app_button("🗺 Открыть карту")]],
            )
        lines = ["📍 <b>Площадки рядом с вами</b>", ""]
        buttons: list[list[Button | None]] = []
        for index, (court, distance, games_today) in enumerate(items, 1):
            icons = "".join(sport_emoji(s) for s in court.sport_types)
            games_text = f"сборов сегодня: {games_today}" if games_today else "сегодня сборов нет"
            lines.append(f"{index}. <b>{esc(court.title)}</b> — {format_distance(distance)}\n      {icons} · {games_text}")
            buttons.append([cb(f"{index}. {court.title[:40]} · {format_distance(distance)}", f"court:{court.id}")])
        buttons.append([self.app_button("🗺 Открыть карту")])
        return View("\n".join(lines), buttons)

    def _join_result_view(self, result: game_service.JoinResult) -> View:
        game = result.game
        if result.confirmed:
            head = "✅ <b>Состав собран!</b> Вы стали последним игроком, остальным участникам ушло уведомление."
        elif result.joined:
            head = "👍 <b>Вы в составе!</b> Бот напишет, когда команда соберётся."
        else:
            head = "ℹ️ Вы уже в составе этого сбора."
        return View(
            head + "\n\n" + self._game_card(game),
            [
                [self.app_button("📍 Открыть площадку", f"court_{game.court_id}")],
                [link("🧭 Маршрут", route_url(game.court.latitude, game.court.longitude))],
                [cb("↩️ Выйти из сбора", f"leave:{game.id}"), cb("🔥 К списку", "find")],
            ],
        )

    def _leave_result_view(self, result: game_service.LeaveResult) -> View:
        game = result.game
        if result.cancelled:
            return View(
                "🗑 Вы вышли из сбора. В нём никого не осталось, поэтому сбор отменён.",
                [[cb("🔥 К списку сборов", "find")], [self.app_button("🗺 Открыть карту")]],
            )
        head = "↩️ Вы вышли из сбора." + (" Набор снова открыт." if result.reopened else "")
        return View(
            head + "\n\n" + self._game_card(game),
            [[cb("➕ Вернуться", f"join:{game.id}"), cb("🔥 К списку", "find")]],
        )

    # --- доставка ----------------------------------------------------------------

    @staticmethod
    def _send(target: dict[str, Any], view: View) -> Action:
        return {"method": "send", **target, "body": view.body()}

    @staticmethod
    def _send_to_user(max_user_id: str, view: View) -> Action:
        return {"method": "send", "user_id": int(max_user_id), "body": view.body()}

    @staticmethod
    def _answer(callback_id: str, view: View) -> Action:
        return {"method": "answer", "callback_id": callback_id, "body": {"message": view.body(replace_keyboard=True)}}

    async def deliver_all(self, actions: list[Action]) -> None:
        if not actions:
            return
        if self.client is None:
            for action in actions:
                body = action["body"].get("message", action["body"])
                logger.info(
                    "[dry-run] %s → %s: %s",
                    action["method"],
                    action.get("user_id") or action.get("chat_id") or action.get("callback_id"),
                    body.get("text", "").replace("\n", " ")[:160],
                )
            return
        for action in actions:
            try:
                await self._deliver(action)
            except (MaxApiError, httpx.HTTPError) as exc:
                logger.warning("Не удалось отправить сообщение в MAX: %s", exc)

    async def _deliver(self, action: Action) -> None:
        # Сообщение могло быть собрано до того, как MAX отклонил open_app, поэтому пересобираем кнопки.
        if not self._open_app_enabled and _has_open_app(action):
            action = self._downgrade_open_app(action)
        try:
            await self._perform(action)
        except MaxApiError as exc:
            if exc.status == 400 and self._open_app_enabled and _has_open_app(action):
                logger.warning("MAX отклонил кнопку open_app (%s) — дальше используем ссылки", exc.body[:200])
                self._open_app_enabled = False
                await self._perform(self._downgrade_open_app(action))
            else:
                raise

    async def _perform(self, action: Action) -> None:
        assert self.client is not None
        if action["method"] == "answer":
            await self.client.answer_callback(action["callback_id"], action["body"])
        else:
            await self.client.send_message(action["body"], chat_id=action.get("chat_id"), user_id=action.get("user_id"))

    def _downgrade_open_app(self, action: Action) -> Action:
        action = copy.deepcopy(action)
        body = action["body"].get("message", action["body"])
        for attachment in body.get("attachments") or []:
            if attachment.get("type") != "inline_keyboard":
                continue
            rows = []
            for row in attachment["payload"]["buttons"]:
                new_row = [
                    self.app_button(button["text"], button.get("payload")) if button.get("type") == "open_app" else button
                    for button in row
                ]
                new_row = [button for button in new_row if button]
                if new_row:
                    rows.append(new_row)
            attachment["payload"]["buttons"] = rows
        return action


def _has_open_app(action: Action) -> bool:
    body = action["body"].get("message", action["body"])
    for attachment in body.get("attachments") or []:
        for row in (attachment.get("payload") or {}).get("buttons") or []:
            if any(button.get("type") == "open_app" for button in row):
                return True
    return False


bot_service = MaxBotService(settings)
