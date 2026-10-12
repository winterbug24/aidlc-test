"""업무 오류와 공통 JSON 오류 응답."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from todo_api.logging_setup import log_event


class ApiError(Exception):
    status_code = 500
    code = "internal_error"
    message = "요청을 처리하는 중 오류가 발생했습니다."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details
        self.headers = headers or {}


class ValidationError(ApiError):
    status_code = 400
    code = "validation_error"
    message = "요청 값이 올바르지 않습니다."


class Unauthorized(ApiError):
    status_code = 401
    code = "unauthorized"
    message = "유효한 API 키가 필요합니다."


class NotFound(ApiError):
    status_code = 404
    code = "not_found"
    message = "요청한 자원을 찾을 수 없습니다."


class DuplicateTitle(ApiError):
    status_code = 409
    code = "duplicate_title"
    message = "같은 제목의 할 일이 이미 있습니다."


class UnsupportedMediaType(ApiError):
    status_code = 415
    code = "unsupported_media_type"
    message = "요청 본문은 application/json 형식이어야 합니다."


class ServiceUnavailable(ApiError):
    status_code = 503
    code = "service_unavailable"
    message = "일시적으로 요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요."


# 프레임워크가 직접 발생시키는 HTTP 오류의 코드와 메시지
_HTTP_ERRORS = {
    400: ("validation_error", "요청 형식이 올바르지 않습니다."),
    404: ("not_found", "요청한 자원을 찾을 수 없습니다."),
    405: ("method_not_allowed", "이 경로에서 지원하지 않는 메서드입니다."),
    413: ("payload_too_large", "요청 본문이 너무 큽니다."),
    415: ("unsupported_media_type", "요청 본문은 application/json 형식이어야 합니다."),
    429: ("rate_limited", "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."),
}
_DEFAULT_RETRY_AFTER_SECONDS = 60


def error_response(
    code: str,
    message: str,
    status: int,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
):
    error: dict[str, object] = {"code": code, "message": message}
    if details:
        error["details"] = details
    response = jsonify({"error": error})
    response.status_code = status
    response.headers.update(headers or {})
    return response


def _retry_after_seconds(exc: HTTPException) -> int:
    explicit = getattr(exc, "retry_after_seconds", None)
    if explicit is not None:
        return int(explicit)
    # Flask-Limiter 예외는 초과된 한도를 들고 있다. 창 길이를 상한으로 안내한다.
    item = getattr(getattr(exc, "limit", None), "limit", None)
    if item is not None:
        return int(item.get_expiry())
    return _DEFAULT_RETRY_AFTER_SECONDS


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return error_response(
            exc.code,
            exc.message,
            exc.status_code,
            details=exc.details,
            headers=exc.headers,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        status = exc.code or 500
        if status >= 500:
            return error_response(ApiError.code, ApiError.message, 500)
        code, message = _HTTP_ERRORS.get(
            status, ("http_error", "요청을 처리할 수 없습니다.")
        )
        headers: dict[str, str] = {}
        if status == 429:
            headers["Retry-After"] = str(_retry_after_seconds(exc))
            log_event(
                "rate_limited",
                "요청 제한 초과",
                level=logging.WARNING,
                remote_addr=request.remote_addr,
                path=request.path,
            )
        elif status == 405:
            valid_methods = getattr(exc, "valid_methods", None)
            if valid_methods:
                headers["Allow"] = ", ".join(sorted(valid_methods))
        return error_response(code, message, status, headers=headers)

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        # 상세는 로그에만 남기고 응답에는 일반 메시지만 보낸다.
        log_event(
            "unhandled_error",
            "처리되지 않은 예외",
            level=logging.ERROR,
            exc_info=exc,
            exception_type=type(exc).__name__,
        )
        return error_response(ApiError.code, ApiError.message, 500)
