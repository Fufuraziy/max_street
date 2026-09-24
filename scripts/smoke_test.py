#!/usr/bin/env python3
"""Smoke-тест MAX Стрит: прогоняет основной пользовательский сценарий через REST API.

Запуск (только стандартная библиотека Python 3.9+):
    python scripts/smoke_test.py                          # напрямую в backend (порт 8000)
    python scripts/smoke_test.py http://localhost:3000    # через Nginx фронтенда
    python scripts/smoke_test.py --full                   # + заявка, новая площадка и выкуп корта

По умолчанию тест не оставляет видимых следов: созданные им сборы в конце отменяются
(платный — через возврат средств с эскроу-счёта). С флагом --full в базе остаются тестовая
заявка, тестовая площадка и один забронированный слот аренды.
"""

from __future__ import annotations

import json
import random
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any

ARGS = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
FULL = "--full" in sys.argv
BASE = (ARGS[0] if ARGS else "http://localhost:8000").rstrip("/")
RUN = random.randint(100000, 999999)
passed = 0


def raw_call(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as err:
        status, payload = err.code, err.read()
    return status, json.loads(payload) if payload else None


def call(method: str, path: str, body: dict[str, Any] | None = None, expected: int = 200) -> Any:
    status, result = raw_call(method, path, body)
    if status != expected:
        raise AssertionError(f"{method} {path}: ожидали {expected}, получили {status}: {result}")
    return result


def check(title: str, condition: bool, details: Any = "") -> None:
    global passed
    if not condition:
        raise AssertionError(f"{title} {details}")
    passed += 1
    print(f"  ✓ {title}")


def main() -> None:
    print(f"MAX Стрит smoke-тест → {BASE}\n")

    print("1. Сервис и бот")
    check("healthcheck", call("GET", "/api/health")["status"] == "ok")
    info = call("GET", "/api/v1/bot/info")
    check(f"бот: режим {info['mode']}, username {info['username']}", "mode" in info)

    print("2. Площадки")
    courts = call("GET", "/api/v1/courts")
    check(f"сид загружен: {len(courts)} площадок", len(courts) >= 15)
    active_games = call("GET", "/api/v1/games")
    check(f"есть активные сборы: {len(active_games)} (сегодня: {sum(c['active_games_today'] for c in courts)})",
          len(active_games) >= 1 and all("active_games_today" in c for c in courts))
    tennis = call("GET", "/api/v1/courts?sport_type=tennis")
    check("фильтр по виду спорта", tennis and all("tennis" in c["sport_types"] for c in tennis))
    bbox = call("GET", "/api/v1/courts?min_lat=59.9&max_lat=59.97&min_lon=30.25&max_lon=30.4")
    check("фильтр по bbox карты", bbox and all(59.9 <= c["latitude"] <= 59.97 for c in bbox))

    court = next(c for c in courts if "basketball" in c["sport_types"])
    detail = call("GET", f"/api/v1/courts/{court['id']}")
    check("карточка площадки содержит лобби и дефекты", "games" in detail and "defects" in detail)
    call("GET", "/api/v1/courts/999999", expected=404)
    check("404 для несуществующей площадки", True)

    print("3. Лобби: создание, кворум, выход")
    start = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    creator = {"creator_max_id": f"smoke_{RUN}_1", "creator_name": "Смоук Создатель"}
    game = call(
        "POST",
        "/api/v1/games",
        {"court_id": court["id"], "sport_type": "basketball", "start_time": start, "required_players": 2,
         "comment": "smoke-тест", **creator},
        expected=201,
    )
    check("лобби создано, создатель стал участником", game["current_players"] == 1 and len(game["participants"]) == 1)

    football_only = next((c for c in courts if "basketball" not in c["sport_types"]), None)
    if football_only:
        error = call(
            "POST",
            "/api/v1/games",
            {"court_id": football_only["id"], "sport_type": "basketball", "start_time": start,
             "required_players": 4, **creator},
            expected=422,
        )
        check("нельзя создать сбор по спорту, которого нет на площадке", "нет условий" in error["detail"])
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    call("POST", "/api/v1/games", {"court_id": court["id"], "sport_type": "basketball", "start_time": past,
                                   "required_players": 4, **creator}, expected=422)
    check("нельзя создать сбор в прошлом", True)

    player = {"user_max_id": f"smoke_{RUN}_2", "user_name": "Смоук Игрок"}
    joined = call("POST", f"/api/v1/games/{game['id']}/join", player)
    check("вступление: кворум набран → confirmed", joined["confirmed"] and joined["game"]["status"] == "confirmed")
    call("POST", f"/api/v1/games/{game['id']}/join", {"user_max_id": f"smoke_{RUN}_3", "user_name": "Третий"},
         expected=409)
    check("в заполненное лобби вступить нельзя (409)", True)
    again = call("POST", f"/api/v1/games/{game['id']}/join", player)
    check("повторное вступление идемпотентно", again["joined"] is False)
    left = call("POST", f"/api/v1/games/{game['id']}/leave", player)
    check("выход: статус вернулся в recruiting", left["game"]["status"] == "recruiting" and left["game"]["current_players"] == 1)
    mine = call("GET", f"/api/v1/games?user_max_id=smoke_{RUN}_1")
    check("«мои игры» возвращают сбор создателя", any(g["id"] == game["id"] for g in mine))
    cancel = call("POST", f"/api/v1/games/{game['id']}/leave", {"user_max_id": creator["creator_max_id"], "user_name": "x"})
    check("последний участник вышел → сбор отменён", cancel["game"]["status"] == "cancelled")

    print("4. Дефекты и краудсорсинг")
    call("POST", f"/api/v1/courts/{court['id']}/defects", {"user_max_id": "x", "defect_type": "earthquake"},
         expected=422)
    check("неизвестный тип поломки отклонён валидацией", True)
    if FULL:
        defect = call("POST", f"/api/v1/courts/{court['id']}/defects",
                      {"user_max_id": f"smoke_{RUN}_1", "defect_type": "broken_ring", "description": "smoke-тест"},
                      expected=201)
        check(f"заявка №{defect['id']}: {defect['status_label']}", defect["status"] == "reported")
        call("POST", f"/api/v1/courts/{court['id']}/defects",
             {"user_max_id": f"smoke_{RUN}_1", "defect_type": "broken_ring"}, expected=409)
        check("повторная заявка о той же проблеме отклонена", True)

        lat, lon = 59.80 + random.random() / 50, 30.10 + random.random() / 50
        new_court = call("POST", "/api/v1/courts", {
            "title": f"Smoke-площадка {RUN}", "sport_types": ["workout"], "address": "Санкт-Петербург, тест",
            "latitude": lat, "longitude": lon, "surface_type": "rubber", "has_lighting": True,
        }, expected=201)
        check("площадка добавлена", new_court["id"] > 0)
        call("POST", "/api/v1/courts", {
            "title": "Дубль", "sport_types": ["workout"], "address": "Санкт-Петербург, тест",
            "latitude": lat + 0.00005, "longitude": lon, "surface_type": "rubber",
        }, expected=409)
        check("дубль в радиусе 30 м отклонён", True)
    else:
        print("  · создание заявки и площадки пропущено (запустите с --full)")

    print("5. Аренда корта и безопасный сбор MAX Escrow (mock СБП / mock-арендодатель)")
    rentals = call("GET", "/api/v1/courts?is_commercial=true")
    check(f"коммерческие корты с ценой: {len(rentals)}", rentals and all(c["price_from"] for c in rentals))
    call("GET", f"/api/v1/courts/{court['id']}/slots", expected=404)
    check("у бесплатной площадки нет расписания аренды (404)", True)

    def free_slot(exclude: set[int]) -> tuple[dict[str, Any], dict[str, Any]]:
        for rental in rentals:
            for offset in range(5):
                day = (date.today() + timedelta(days=offset)).isoformat()
                for slot in call("GET", f"/api/v1/courts/{rental['id']}/slots?date={day}"):
                    if slot["is_available"] and slot["id"] not in exclude:
                        return rental, slot
        raise AssertionError("не найден свободный слот аренды")

    rental, slot = free_slot(set())
    check(f"расписание от mock-провайдера: {slot['start_time'][:16]} · {slot['price']} ₽", slot["duration_minutes"] > 0)
    sport = rental["sport_types"][0]
    call("POST", "/api/v1/games", {"court_id": rental["id"], "sport_type": sport, "start_time": slot["start_time"],
                                   "required_players": 3, **creator}, expected=422)
    check("для коммерческого корта слот обязателен (422)", True)
    paid_game = call("POST", "/api/v1/games", {"court_id": rental["id"], "sport_type": sport, "slot_id": slot["id"],
                                               "required_players": 3, **creator}, expected=201)
    check(f"платное лобби: эскроу-счёт {paid_game['escrow_account_id']}",
          re.fullmatch(r"ESC-\d{4}-[0-9A-F]{4}", paid_game["escrow_account_id"] or "") is not None
          and paid_game["total_cost"] == slot["price"] and paid_game["payment_status"] == "pending")
    day = slot["start_time"][:10]
    slot_status = {s["id"]: s["status"] for s in call("GET", f"/api/v1/courts/{rental['id']}/slots?date={day}")}
    check("слот временно зарезервирован за сбором", slot_status.get(slot["id"]) == "reserved")
    call("POST", "/api/v1/games", {"court_id": rental["id"], "sport_type": sport, "slot_id": slot["id"],
                                   "required_players": 3, "creator_max_id": f"smoke_{RUN}_9", "creator_name": "Второй"},
         expected=409)
    check("второй сбор на тот же слот отклонён (409)", True)

    call("POST", f"/api/v1/games/{paid_game['id']}/pay", {"user_max_id": player["user_max_id"]}, expected=404)
    check("оплатить можно только после вступления", True)
    share = paid_game["share_amount"]
    paid = call("POST", f"/api/v1/games/{paid_game['id']}/pay",
                {"user_max_id": creator["creator_max_id"], "amount": share, "payment_method": "sbp_mock"})
    check(f"взнос организатора {share} ₽ заморожен на эскроу", paid["game"]["collected_amount"] == share and not paid["booked"])
    call("POST", f"/api/v1/games/{paid_game['id']}/join", player)
    call("POST", f"/api/v1/games/{paid_game['id']}/pay", {"user_max_id": player["user_max_id"], "amount": 1}, expected=422)
    check("неверная сумма доли отклонена (422)", True)
    paid = call("POST", f"/api/v1/games/{paid_game['id']}/pay", {"user_max_id": player["user_max_id"]})
    check("кворум не набран — сбор средств продолжается", paid["game"]["payment_status"] == "pending"
          and paid["game"]["paid_count"] == 2)
    expired = call("POST", f"/api/v1/mock/escrow/{paid_game['id']}/expire")
    check("дедлайн: средства возвращены, лобби отменено",
          expired["game"]["payment_status"] == "refunded" and expired["game"]["status"] == "cancelled"
          and len(expired["refunds"]) == 2)
    statement = call("GET", f"/api/v1/games/{paid_game['id']}/escrow")
    kinds = [tx["kind"] for tx in statement["transactions"]]
    check("выписка эскроу: 2 взноса, 2 возврата, баланс 0",
          kinds.count("deposit") == 2 and kinds.count("refund") == 2 and statement["balance"] == 0)
    slot_status = {s["id"]: s["status"] for s in call("GET", f"/api/v1/courts/{rental['id']}/slots?date={day}")}
    check("слот снова свободен", slot_status.get(slot["id"]) == "free")

    if FULL:
        rental, slot = free_slot({slot["id"]})
        duo = call("POST", "/api/v1/games", {"court_id": rental["id"], "sport_type": rental["sport_types"][0],
                                             "slot_id": slot["id"], "required_players": 2, **creator}, expected=201)
        call("POST", f"/api/v1/games/{duo['id']}/pay", {"user_max_id": creator["creator_max_id"]})
        call("POST", f"/api/v1/games/{duo['id']}/join", player)
        done = call("POST", f"/api/v1/games/{duo['id']}/pay", {"user_max_id": player["user_max_id"]})
        check(f"100% собрано → корт выкуплен, бронь #{done['booking_reference']}",
              done["booked"] and done["game"]["status"] == "booked" and done["game"]["payment_status"] == "paid_to_court"
              and (done["booking_reference"] or "").startswith("MAX-SPORT-"))
        statement = call("GET", f"/api/v1/games/{duo['id']}/escrow")
        check("выписка: выплата арендодателю, баланс 0",
              [tx["kind"] for tx in statement["transactions"]].count("payout") == 1 and statement["balance"] == 0)
        received = call("GET", "/api/v1/mock/provider/bookings")["bookings"]
        check("mock-арендодатель получил вебхук брони", any(b["booking_reference"] == done["booking_reference"] for b in received))
        call("POST", f"/api/v1/games/{duo['id']}/leave", player, expected=409)
        check("из оплаченного сбора выйти нельзя (409)", True)
    else:
        print("  · полный выкуп корта пропущен (запустите с --full)")

    print("6. Чат-бот (webhook)")
    user = {"user_id": 7000000 + RUN, "first_name": "Смоук", "name": "Смоук", "is_bot": False}

    def update_for(text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {"update_type": "message_created", "timestamp": 0,
                "message": {"sender": user, "recipient": {"chat_id": 1, "chat_type": "dialog"},
                            "body": {"mid": "m", "seq": 1, "text": text, "attachments": attachments or []}}}

    def say(text: str, attachments: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        return call("POST", "/api/v1/bot/webhook", update_for(text, attachments))["replies"]

    if info["mode"] == "webhook":
        print("  · режим webhook: ответы уходят в MAX, проверка пропущена, чтобы не слать тестовые сообщения")
        print(f"\nВсе проверки пройдены: {passed} ✓")
        return
    status, probe = raw_call("POST", "/api/v1/bot/webhook", update_for("/start"))
    if status == 401:
        print("  · webhook защищён MAX_WEBHOOK_SECRET, проверка бота пропущена")
        print(f"\nВсе проверки пройдены: {passed} ✓")
        return
    start_reply = probe["replies"]
    check("/start → приветствие с кнопкой мини-приложения", "MAX Стрит" in start_reply[0]["body"]["text"])
    find_reply = say("/find")
    check("/find → список ближайших сборов", "сбор" in find_reply[0]["body"]["text"].lower())
    check("свободный текст «хочу в футбол» → сборы по футболу", "футбол" in say("хочу в футбол")[0]["body"]["text"].lower())
    near = say("", [{"type": "location", "latitude": 59.9386, "longitude": 30.3141}])
    check("геолокация → ближайшие площадки", "рядом" in near[0]["body"]["text"])
    check("/help", "/find" in say("/help")[0]["body"]["text"])
    callback = {"update_type": "message_callback", "timestamp": 0,
                "callback": {"timestamp": 0, "callback_id": "cb1", "payload": f"court:{court['id']}", "user": user}}
    court_reply = call("POST", "/api/v1/bot/webhook", callback)["replies"]
    check("callback «court:<id>» → карточка площадки", court_reply[0]["method"] == "answer")

    print(f"\nВсе проверки пройдены: {passed} ✓")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\n✗ ОШИБКА: {exc}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"\n✗ Сервис недоступен ({BASE}): {exc}")
        sys.exit(2)
