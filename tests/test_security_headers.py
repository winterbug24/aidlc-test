"""보안 헤더 테스트 (예제 기반): 응답 종류를 가리지 않고 같은 헤더가 붙는다."""

from __future__ import annotations

import pytest

from conftest import AUTH, make_config
from todo_api import repository
from todo_api.app import create_app
from todo_api.security_headers import CONTENT_SECURITY_POLICY, CSP_DIRECTIVES

EXPECTED_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


def assert_security_headers(response) -> None:
    for name, value in EXPECTED_HEADERS.items():
        assert response.headers.get(name) == value, name
    assert len(response.headers["X-Request-ID"]) == 32
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize(
    ("path", "headers", "status"),
    [
        ("/todo_list", {}, 200),
        ("/todo_list/app.css", {}, 200),
        ("/todo_list/app.js", {}, 200),
        ("/todo_list/missing.js", {}, 404),
        ("/health", {}, 200),
        ("/todos", AUTH, 200),
        ("/todos", {}, 401),
        ("/todos/999", AUTH, 404),
        ("/nope", {}, 404),
    ],
)
def test_every_kind_of_response_carries_security_headers(client, path, headers, status):
    response = client.get(path, headers=headers)
    assert response.status_code == status
    assert_security_headers(response)


def test_error_responses_carry_security_headers(client, monkeypatch):
    created = client.post("/todos", json={"title": "a"}, headers=AUTH)
    assert_security_headers(created)
    assert_security_headers(client.post("/todos", json={"title": "A"}, headers=AUTH))  # 409
    assert_security_headers(client.put("/todos/1", json={}, headers=AUTH))  # 405
    assert_security_headers(client.delete("/todos/1", headers=AUTH))  # 204

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(repository, "list_todos", boom)
    failed = client.get("/todos", headers=AUTH)
    assert failed.status_code == 500
    assert_security_headers(failed)


def test_rate_limited_response_carries_security_headers(tmp_path):
    config = make_config(tmp_path, rate_limit_enabled=True, rate_limit_default="1 per hour")
    client = create_app(config).test_client()
    client.get("/health")
    limited = client.get("/todo_list")
    assert limited.status_code == 429
    assert_security_headers(limited)


def test_policy_blocks_everything_by_default_and_allows_only_same_origin():
    directives = dict(CSP_DIRECTIVES)
    assert directives["default-src"] == "'none'"
    assert directives["script-src"] == "'self'"
    assert directives["style-src"] == "'self'"
    assert directives["connect-src"] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert directives["base-uri"] == "'none'"
    assert directives["form-action"] == "'none'"


def test_policy_never_allows_inline_or_eval_or_external_sources():
    for forbidden in ["unsafe-inline", "unsafe-eval", "http:", "https:", "*"]:
        assert forbidden not in CONTENT_SECURITY_POLICY
    # data:는 빈 아이콘 선언을 위한 이미지에만 허용한다.
    assert CONTENT_SECURITY_POLICY.count("data:") == 1
    assert dict(CSP_DIRECTIVES)["img-src"] == "'self' data:"
