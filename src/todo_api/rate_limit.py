"""요청 제한: 전체 한도와 인증 실패 한도."""

from __future__ import annotations

from flask import Flask, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from limits import parse
from werkzeug.exceptions import TooManyRequests

from todo_api.config import Config

_LIMITER_KEY = "todo_api.limiter"
_AUTH_LIMIT_KEY = "todo_api.auth_failure_limit"
_AUTH_FAILURE_SCOPE = "auth-failure"


def init_rate_limiting(app: Flask, config: Config) -> None:
    app.config["RATELIMIT_ENABLED"] = config.rate_limit_enabled
    # 클라이언트 식별은 직접 연결된 원격 주소만 쓴다. 프록시 헤더는 신뢰하지 않는다.
    # application_limits는 모든 라우트가 한 카운터를 공유한다(라우트별 한도가 아님).
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        application_limits=[config.rate_limit_default],
        storage_uri="memory://",
        strategy="fixed-window",
    )
    app.extensions[_LIMITER_KEY] = limiter
    app.extensions[_AUTH_LIMIT_KEY] = parse(config.rate_limit_auth_failure)


def check_auth_failure_limit() -> None:
    """인증 실패가 한도를 넘은 주소는 키를 비교하기 전에 막는다.

    키가 맞는지 확인한 뒤에 막으면 대입 공격을 제한하지 못한다.
    """
    if not current_app.config["RATELIMIT_ENABLED"]:
        return
    limit = current_app.extensions[_AUTH_LIMIT_KEY]
    strategy = current_app.extensions[_LIMITER_KEY].limiter
    if not strategy.test(limit, _AUTH_FAILURE_SCOPE, get_remote_address()):
        exc = TooManyRequests()
        exc.retry_after_seconds = limit.get_expiry()
        raise exc


def record_auth_failure() -> None:
    if not current_app.config["RATELIMIT_ENABLED"]:
        return
    limit = current_app.extensions[_AUTH_LIMIT_KEY]
    strategy = current_app.extensions[_LIMITER_KEY].limiter
    strategy.hit(limit, _AUTH_FAILURE_SCOPE, get_remote_address())
