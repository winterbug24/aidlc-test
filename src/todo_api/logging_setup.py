"""JSON 구조화 로깅과 요청 단위 훅."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, g, has_request_context, request
from werkzeug.exceptions import RequestEntityTooLarge

from todo_api.config import ensure_private_dir

LOGGER_NAME = "todo_api"
LOG_FILE_NAME = "todo-api.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

_CORE_KEYS = ("timestamp", "level", "request_id", "event", "message")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "request_id": g.get("request_id") if has_request_context() else None,
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
        }
        for key, value in getattr(record, "fields", {}).items():
            if key not in _CORE_KEYS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class PrivateRotatingFileHandler(RotatingFileHandler):
    """순환으로 새로 만들어지는 파일도 소유자 전용 권한으로 연다."""

    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return os.fdopen(fd, self.mode, encoding=self.encoding, errors=self.errors)


def configure_logging(log_dir: Path | None, *, to_stdout: bool = True) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # 앱을 다시 만들 때 이전에 붙인 처리기가 중복되지 않게 정리한다.
    for handler in list(logger.handlers):
        if getattr(handler, "_todo_api_managed", False):
            logger.removeHandler(handler)
            handler.close()

    handlers: list[logging.Handler] = []
    if to_stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    if log_dir is not None:
        ensure_private_dir(log_dir)
        handlers.append(
            PrivateRotatingFileHandler(
                log_dir / LOG_FILE_NAME,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
        )
    for handler in handlers:
        handler.setFormatter(JsonFormatter())
        handler._todo_api_managed = True
        logger.addHandler(handler)


def log_event(
    event: str,
    message: str,
    *,
    level: int = logging.INFO,
    exc_info: BaseException | None = None,
    **fields: object,
) -> None:
    logging.getLogger(LOGGER_NAME).log(
        level,
        message,
        exc_info=exc_info,
        extra={"event": event, "fields": fields},
    )


def register_request_hooks(app: Flask) -> None:
    @app.before_request
    def start_request() -> None:
        # 클라이언트가 보낸 요청 ID는 쓰지 않고 항상 새로 만든다.
        g.request_id = uuid.uuid4().hex
        g.request_started = time.perf_counter()
        max_length = app.config["MAX_CONTENT_LENGTH"]
        if request.content_length is not None and request.content_length > max_length:
            raise RequestEntityTooLarge()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        started = g.get("request_started")
        duration_ms = (
            round((time.perf_counter() - started) * 1000, 2) if started else None
        )
        log_event(
            "request",
            "요청 처리 완료",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            remote_addr=request.remote_addr,
        )
        return response
