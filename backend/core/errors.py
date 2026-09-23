"""Доменные ошибки. Сервисы бросают их, а API и бот превращают в ответ пользователю."""

from __future__ import annotations


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class ValidationFailedError(DomainError):
    status_code = 422


class TooManyRequestsError(DomainError):
    status_code = 429
