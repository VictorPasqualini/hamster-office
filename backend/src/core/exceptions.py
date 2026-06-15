"""Erros de domínio + handlers problem+json."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    error_type = "app_error"

    def __init__(self, detail: str, status_code: int | None = None):
        self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(detail)


class NotFound(AppError):
    status_code = 404
    error_type = "not_found"


class Unauthorized(AppError):
    status_code = 401
    error_type = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    error_type = "forbidden"


class Conflict(AppError):
    status_code = 409
    error_type = "conflict"


def _problem(status: int, type_: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": f"https://errors.hamster.office/{type_}",
            "title": type_.replace("_", " ").title(),
            "status": status,
            "detail": detail,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _problem(exc.status_code, exc.error_type, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _problem(422, "validation", str(exc.errors()))
