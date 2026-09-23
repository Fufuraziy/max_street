"""Общие типы для Pydantic-схем."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, PlainSerializer


def _strip_required(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("Поле не может быть пустым")
    return value


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lstrip("@")
    return value or None


MaxUserId = Annotated[str, Field(min_length=1, max_length=64, examples=["123456789"]), AfterValidator(_strip_required)]
PersonName = Annotated[str, Field(min_length=1, max_length=64, examples=["Артём"]), AfterValidator(_strip_required)]
Username = Annotated[Annotated[str, Field(max_length=64)] | None, AfterValidator(_strip_optional)]

# Деньги храним в Decimal (NUMERIC(10,2)), а в JSON отдаём числом — так проще фронтенду.
Money = Annotated[Decimal, PlainSerializer(lambda value: float(value), return_type=float, when_used="json")]
