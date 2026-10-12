"""API 키 인증."""

from __future__ import annotations

import hashlib
import hmac
import logging

from flask import current_app, request

from todo_api.errors import Unauthorized
from todo_api.logging_setup import log_event
from todo_api.rate_limit import check_auth_failure_limit, record_auth_failure

API_KEY_HEADER = "X-API-Key"


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def require_api_key() -> None:
    """보호 라우트의 요청 전처리 훅. 실패하면 항상 같은 401을 돌려준다."""
    check_auth_failure_limit()
    expected = current_app.config["TODO_CONFIG"].api_key
    provided = request.headers.get(API_KEY_HEADER, "")
    # 해시한 뒤 상수 시간으로 비교해 길이와 내용이 응답 시간으로 드러나지 않게 한다.
    if hmac.compare_digest(_digest(provided), _digest(expected)):
        return
    record_auth_failure()
    log_event(
        "auth_failed",
        "API 키 인증 실패",
        level=logging.WARNING,
        remote_addr=request.remote_addr,
        path=request.path,
    )
    raise Unauthorized()
