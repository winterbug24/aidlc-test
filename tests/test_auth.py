"""인증 테스트 (예제 기반): 기본 거부, 공개 라우트, 정보 비노출."""

from __future__ import annotations

import pytest

from conftest import AUTH, TEST_API_KEY

PROTECTED_REQUESTS = [
    ("post", "/todos", {"json": {"title": "a"}}),
    ("get", "/todos", {}),
    ("get", "/todos/1", {}),
    ("patch", "/todos/1", {"json": {"completed": True}}),
    ("delete", "/todos/1", {}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_REQUESTS)
def test_protected_routes_require_api_key(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "key", ["", "wrong", TEST_API_KEY + "x", TEST_API_KEY[:-1], TEST_API_KEY.swapcase()]
)
def test_wrong_api_key_is_rejected(client, key):
    assert client.get("/todos", headers={"X-API-Key": key}).status_code == 401


def test_bearer_header_is_not_accepted(client):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    assert client.get("/todos", headers=headers).status_code == 401


def test_valid_api_key_is_accepted(client):
    assert client.get("/todos", headers=AUTH).status_code == 200


def test_unauthenticated_caller_learns_nothing_about_resources(client, create):
    todo = create("a")
    existing = client.get(f"/todos/{todo['id']}")
    missing = client.get("/todos/999")
    assert existing.status_code == missing.status_code == 401
    assert existing.get_json() == missing.get_json()


def test_authentication_is_checked_before_validation(client):
    response = client.post("/todos", json={"unknown": 1})
    assert response.status_code == 401


def test_failed_authentication_changes_nothing(client, create):
    todo = create("a")
    client.delete(f"/todos/{todo['id']}")
    client.patch(f"/todos/{todo['id']}", json={"completed": True})
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": [todo]}


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_auth_failure_is_logged_without_the_key(client, events):
    client.get("/todos", headers={"X-API-Key": "attempted-secret-value"})
    client.get("/todos", headers=AUTH)

    failures = events.named("auth_failed")
    assert len(failures) == 1
    assert failures[0]["path"] == "/todos"
    logged = " ".join(f"{r.getMessage()} {r.fields}" for r in events.records)
    assert "attempted-secret-value" not in logged
    assert TEST_API_KEY not in logged
