"""공용 픽스처와 도우미."""

from __future__ import annotations

import logging
import secrets
import sqlite3
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from hypothesis import settings
from werkzeug.serving import make_server

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


# --- 브라우저 테스트 장치 (Playwright) ---


@dataclass
class LiveServer:
    """임의의 빈 포트에서 실제로 돌고 있는 앱."""

    url: str
    config: Config
    app: object

    @property
    def page_url(self) -> str:
        return f"{self.url}/api_test"

    def seed(self, *titles: str) -> list[dict]:
        """화면을 거치지 않고 API로 준비 데이터를 넣는다. 넣은 순서대로 돌려준다."""
        client = self.app.test_client()
        created = []
        for title in titles:
            response = client.post("/todos", json={"title": title}, headers=AUTH)
            assert response.status_code == 201, response.get_data(as_text=True)
            created.append(response.get_json())
        return created

    def complete(self, todo: dict) -> None:
        response = self.app.test_client().patch(
            f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH
        )
        assert response.status_code == 200

    def delete(self, todo: dict) -> None:
        response = self.app.test_client().delete(f"/todos/{todo['id']}", headers=AUTH)
        assert response.status_code == 204

    def seed_many(self, count: int) -> None:
        """많은 항목은 DB에 직접 넣는다."""
        rows = [
            (f"할 일 {index:04d}", f"2026-01-01T00:{index // 60:02d}:{index % 60:02d}.000000Z")
            for index in range(count)
        ]
        conn = sqlite3.connect(self.config.db_path)
        try:
            with conn:
                conn.executemany(
                    "INSERT INTO todos (title, completed, created_at) VALUES (?, 0, ?)", rows
                )
        finally:
            conn.close()

    def titles(self) -> list[str]:
        response = self.app.test_client().get("/todos", headers=AUTH)
        return [todo["title"] for todo in response.get_json()["todos"]]


@contextmanager
def running_server(config: Config) -> Iterator[LiveServer]:
    """주어진 설정의 앱을 임의의 빈 포트에 띄운다."""
    app = create_app(config)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield LiveServer(f"http://127.0.0.1:{server.server_port}", config, app)
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture
def live_server(tmp_path: Path) -> Iterator[LiveServer]:
    with running_server(make_config(tmp_path)) as server:
        yield server


class Ui:
    """화면 조작 도우미. 요소는 data-testid로만 찾는다."""

    def __init__(self, page, server: LiveServer) -> None:
        self.page = page
        self.server = server
        self.problems: list[str] = []
        self.requests: list[str] = []
        page.on("console", self._on_console)
        page.on("pageerror", lambda error: self.problems.append(f"pageerror: {error}"))
        page.on("request", lambda request: self.requests.append(request.url))

    def _on_console(self, message) -> None:
        # 4xx/5xx 응답을 받으면 브라우저가 남기는 기록은 의도한 상황이라 제외한다.
        # 콘텐츠 보안 정책 위반과 스크립트 오류는 여기서 걸린다.
        if message.type == "error" and not message.text.startswith("Failed to load resource"):
            self.problems.append(f"console: {message.text}")

    def tid(self, name: str):
        return self.page.get_by_test_id(name)

    def open(self) -> None:
        self.page.goto(self.server.page_url)

    def login(self) -> None:
        """키를 입력해 목록 화면까지 간다."""
        self.open()
        self.tid("key-form-input").fill(TEST_API_KEY)
        self.tid("key-form-submit-button").click()
        self.tid("list-view").wait_for(state="visible")

    def item(self, title: str):
        return self.tid("todo-item").filter(
            has=self.tid("todo-item-title").get_by_text(title, exact=True)
        )

    def titles(self) -> list[str]:
        return self.tid("todo-item-title").all_inner_texts()

    def add(self, title: str) -> None:
        self.tid("add-form-input").fill(title)
        self.tid("add-form-input").press("Enter")

    def stored_key(self) -> str | None:
        return self.page.evaluate("() => window.localStorage.getItem('todoApiKey')")

    def api_requests(self) -> list[str]:
        return [url for url in self.requests if "/todos" in url]


@pytest.fixture
def ui(page, live_server: LiveServer) -> Iterator[Ui]:
    session = Ui(page, live_server)
    yield session
    # 스크립트 오류나 콘텐츠 보안 정책 위반이 한 번이라도 있으면 실패다.
    assert session.problems == []
