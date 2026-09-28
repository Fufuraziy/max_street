"""Шина событий (EventBus) для Server-Sent Events (SSE) в реальном времени.

Позволяет фронтенду и мобильным клиентам мгновенно получать обновления лобби
(вступление участников, внесение долей эскроу, сбор кворума, бронь) без постоянного поллинга.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)


class GameEventBus:
    """Асинхронная шина событий для рассылки обновлений лобби клиентам."""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, game_id: int) -> AsyncIterator[dict[str, Any]]:
        """Подписка на события конкретного лобби (генератор для SSE-потока)."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        async with self._lock:
            self._subscribers.setdefault(game_id, set()).add(queue)

        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            async with self._lock:
                if game_id in self._subscribers:
                    self._subscribers[game_id].discard(queue)
                    if not self._subscribers[game_id]:
                        del self._subscribers[game_id]

    async def publish(self, game_id: int, event_type: str, data: dict[str, Any]) -> None:
        """Публикация события для всех активных подписчиков лобби."""
        async with self._lock:
            queues = list(self._subscribers.get(game_id, set()))

        if not queues:
            return

        message = {"event": event_type, "data": data}
        for queue in queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Очередь клиента переполнена для game_id=%s, событие пропущено", game_id)


event_bus = GameEventBus()
