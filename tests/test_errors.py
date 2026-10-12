"""오류 응답과 공통 응답 헤더 테스트 (예제 기반)."""

from __future__ import annotations

import json
import logging

from conftest import AUTH, make_config
from todo_api import repository
from todo_api.app import create_app
from todo_api.logging_setup import LOG_FILE_NAME, LOGGER_NAME


def error_of(response) -> dict:
    assert response.mimetype == "application/json"
    return response.get_json()["error"]


def test_unknown_path_is_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert error_of(response)["code"] == "not_found"


def test_unsupported_method_is_json_405_with_allow_header(client):
    response = client.put("/todos/1", json={}, headers=AUTH)
    assert response.status_code == 405
    assert error_of(response)["code"] == "method_not_allowed"
    assert "PATCH" in response.headers["Allow"]


def test_oversized_body_is_413(client):
    response = client.post("/todos", json={"title": "a" * 20_000}, headers=AUTH)
    assert response.status_code == 413
    assert error_of(response)["code"] == "payload_too_large"


def test_oversized_body_is_rejected_before_authentication(client):
    assert client.post("/todos", json={"title": "a" * 20_000}).status_code == 413


def test_deeply_nested_json_is_a_validation_error(client):
    body = "[" * 5000 + "]" * 5000
    response = client.post(
        "/todos", data=body, content_type="application/json", headers=AUTH
    )
    assert response.status_code == 400


def test_unexpected_error_returns_generic_500_and_logs_details(client, events, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret detail at /home/user/app.py")

    monkeypatch.setattr(repository, "list_todos", boom)
    response = client.get("/todos", headers=AUTH)

    assert response.status_code == 500
    assert error_of(response)["code"] == "internal_error"
    text = response.get_data(as_text=True)
    for leaked in ["secret detail", "/home/user", "RuntimeError", "Traceback"]:
        assert leaked not in text
    assert events.named("unhandled_error")[0]["exception_type"] == "RuntimeError"


def test_every_response_has_request_id_and_hardening_headers(client):
    first = client.get("/health")
    second = client.get("/todos")  # 401
    third = client.get("/nope")  # 404
    for response in (first, second, third):
        assert len(response.headers["X-Request-ID"]) == 32
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"
        assert "Access-Control-Allow-Origin" not in response.headers
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_client_supplied_request_id_is_ignored(client):
    response = client.get("/health", headers={"X-Request-ID": "forged"})
    assert response.headers["X-Request-ID"] != "forged"


def test_request_log_carries_method_path_status_and_request_id(client, events):
    response = client.get("/health")
    request_logs = events.named("request")
    assert len(request_logs) == 1
    assert request_logs[0]["method"] == "GET"
    assert request_logs[0]["path"] == "/health"
    assert request_logs[0]["status"] == 200
    assert response.headers["X-Request-ID"]


def test_log_file_contains_one_json_object_per_line(tmp_path):
    log_dir = tmp_path / "logs"
    client = create_app(make_config(tmp_path, log_dir=log_dir)).test_client()
    response = client.get("/health")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()

    lines = (log_dir / LOG_FILE_NAME).read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines]
    request_entry = next(e for e in entries if e["event"] == "request")
    assert request_entry["request_id"] == response.headers["X-Request-ID"]
    assert {"timestamp", "level", "message", "status", "duration_ms"} <= set(request_entry)
    assert request_entry["timestamp"].endswith("Z")
