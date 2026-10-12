"""복원력 테스트 (RT-01~04). RT-05~07은 test_backup.py, RT-08은 test_config.py."""

from __future__ import annotations

import sqlite3

import pytest

from conftest import AUTH, capture_events, make_config
from todo_api import repository
from todo_api.app import create_app


def corrupt_database(db_path) -> None:
    for suffix in ("-wal", "-shm"):
        db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)
    db_path.write_bytes(b"this is not a database file " * 200)


@pytest.fixture
def fast_timeout_config(tmp_path):
    # 잠금 대기 시간을 줄여 테스트가 빨리 끝나게 한다.
    return make_config(tmp_path, db_timeout_seconds=0.05)


def test_rt01_locked_database_is_retried_once_then_503(fast_timeout_config):
    client = create_app(fast_timeout_config).test_client()
    blocker = sqlite3.connect(fast_timeout_config.db_path)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with capture_events() as events:
            response = client.post("/todos", json={"title": "a"}, headers=AUTH)
            # WAL 모드에서는 쓰기 잠금 중에도 읽기가 가능하다.
            read = client.get("/todos", headers=AUTH)
    finally:
        blocker.rollback()
        blocker.close()

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "service_unavailable"
    assert response.headers["Retry-After"] == "5"
    assert events.named("db_retry") == [{"operation": "create_todo"}]
    assert read.status_code == 200

    # 잠금이 풀리면 정상 동작하고, 실패한 요청은 반영되지 않았다.
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": []}
    assert client.post("/todos", json={"title": "a"}, headers=AUTH).status_code == 201


def test_rt02_request_succeeds_when_lock_clears_before_retry(client, events, monkeypatch):
    real_create = repository.create_todo
    calls = []

    def locked_once(conn, title):
        calls.append(title)
        if len(calls) == 1:
            raise sqlite3.OperationalError("database is locked")
        return real_create(conn, title)

    monkeypatch.setattr(repository, "create_todo", locked_once)
    response = client.post("/todos", json={"title": "a"}, headers=AUTH)

    assert response.status_code == 201
    assert len(calls) == 2
    assert len(events.named("db_retry")) == 1


def test_only_lock_errors_are_retried(client, events, monkeypatch):
    calls = []

    def io_error(conn, title):
        calls.append(title)
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repository, "create_todo", io_error)
    response = client.post("/todos", json={"title": "a"}, headers=AUTH)

    assert response.status_code == 500
    assert len(calls) == 1
    assert events.named("db_retry") == []


def test_rt03_health_reports_503_when_database_is_unreadable(client, config):
    corrupt_database(config.db_path)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "service_unavailable"


def test_rt04_database_failure_returns_generic_error_without_internals(
    client, config, events
):
    corrupt_database(config.db_path)
    for response in (
        client.get("/todos", headers=AUTH),
        client.post("/todos", json={"title": "a"}, headers=AUTH),
    ):
        assert response.status_code == 500
        assert response.get_json()["error"]["code"] == "internal_error"
        text = response.get_data(as_text=True).lower()
        for leaked in ["sqlite", "not a database", str(config.db_path).lower(), "traceback"]:
            assert leaked not in text
    assert len(events.named("unhandled_error")) == 2
