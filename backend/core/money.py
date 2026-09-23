"""Денежные суммы: Decimal с точностью до копейки и форматирование «1 800 ₽»."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
NBSP = " "


def to_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_rub(value: Decimal | int | float) -> str:
    amount = to_money(value)
    if amount == amount.to_integral_value():
        text = f"{int(amount):,}"
    else:
        text = f"{amount:,.2f}".replace(".", "#")
    return text.replace(",", NBSP).replace("#", ",") + f"{NBSP}₽"
