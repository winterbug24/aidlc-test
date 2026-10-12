"""Waitress로 앱을 실행하는 진입점: python -m todo_api.server"""

from __future__ import annotations

import logging
import sys

from waitress import serve

from todo_api.app import create_app
from todo_api.config import Config, ConfigError
from todo_api.logging_setup import log_event

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def main() -> int:
    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"설정 오류: {exc}", file=sys.stderr)
        return 2

    app = create_app(config)
    if config.host not in _LOOPBACK_HOSTS:
        log_event(
            "startup_warning",
            "루프백이 아닌 주소에 바인딩합니다. 외부에서 접근할 수 있습니다.",
            level=logging.WARNING,
            host=config.host,
        )
    log_event("startup", "서버 시작", host=config.host, port=config.port)
    # ident=None: 응답의 Server 헤더로 서버 종류와 버전을 알리지 않는다.
    serve(app, host=config.host, port=config.port, ident=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
