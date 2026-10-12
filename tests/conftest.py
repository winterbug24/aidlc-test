"""공용 픽스처와 도우미."""

from __future__ import annotations

import logging
import secrets
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import settings

from todo_api.app import create_app
from todo_api.config import Config
from todo_api.logging_setup import LOGGER_NAME

# 축소(shrinking)는 기본값 그대로 두고, 실패 시 재현 정보를 출력한다.
settings.register_profile("default", deadline=None, print_blob=True)
settings.load_profile("default")

# 테스트 실행마다 새로 만든다. 소스에 고정된 키를 두지 않는다.
TEST_API_KEY = secrets.token_urlsafe(32)
AUTH = {"X-API-Key": TEST_API_KEY}


def make_config(base_dir: Path, **overrides) -> Config:
    values = {
        "api_key": TEST_API_KEY,
        "db_path": base_dir / "instance" / "todo.db",
        "log_dir": None,
        "backup_dir": base_dir / "backups",
        "log_to_stdout": False,
        "rate_limit_enabled": False,
    }
    values.update(overrides)
    return Config(**values)


@contextmanager
def fresh_client(**overrides) -> Iterator:
    """임시 DB를 쓰는 독립된 앱의 테스트 클라이언트. 속성 기반 테스트의 예제마다 사용한다."""
    with tempfile.TemporaryDirectory() as tmp:
        yield create_app(make_config(Path(tmp), **overrides)).test_client()


class EventCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def named(self, event: str) -> list[dict]:
        return [r.fields for r in self.records if getattr(r, "event", None) == event]


@contextmanager
def capture_events() -> Iterator[EventCollector]:
    """앱을 만든 뒤에 사용한다. 로그 이벤트를 모아 검증할 수 있게 한다."""
    collector = EventCollector()
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(collector)
    try:
        yield collector
    finally:
        logger.removeHandler(collector)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return make_config(tmp_path)


@pytest.fixture
def app(config: Config):
    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def events(app) -> Iterator[EventCollector]:
    with capture_events() as collector:
        yield collector


@pytest.fixture
def create(client):
    """제목으로 할 일을 만들고 응답 본문을 돌려주는 도우미."""

    def _create(title: str) -> dict:
        response = client.post("/todos", json={"title": title}, headers=AUTH)
        assert response.status_code == 201, response.get_data(as_text=True)
        return response.get_json()

    return _create
