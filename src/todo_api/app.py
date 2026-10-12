"""앱 팩토리."""

from __future__ import annotations

from flask import Flask

from todo_api.config import Config
from todo_api.db import close_db, init_db
from todo_api.errors import register_error_handlers
from todo_api.logging_setup import configure_logging, register_request_hooks
from todo_api.rate_limit import init_rate_limiting
from todo_api.routes import health, todos, web
from todo_api.security_headers import register_security_headers


def create_app(config: Config | None = None) -> Flask:
    """설정을 받아 앱을 조립한다. 설정이 없으면 환경 변수에서 읽는다."""
    config = config or Config.from_env()

    # 기본 정적 파일 경로는 끈다. 화면 파일은 routes/web.py가 정해 둔 것만 제공한다.
    app = Flask(__name__, static_folder=None)
    app.config["TODO_CONFIG"] = config
    app.config["MAX_CONTENT_LENGTH"] = config.max_content_length
    app.debug = False
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    configure_logging(config.log_dir, to_stdout=config.log_to_stdout)
    init_db(config.db_path, config.db_timeout_seconds)

    # 등록 순서가 요청 처리 순서다: 요청 ID와 크기 확인, 요청 제한, 그다음 라우트별 인증.
    register_request_hooks(app)
    register_security_headers(app)
    init_rate_limiting(app, config)
    app.teardown_appcontext(close_db)
    register_error_handlers(app)

    app.register_blueprint(todos.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(web.bp)
    return app
