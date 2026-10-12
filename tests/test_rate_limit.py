"""요청 제한 테스트 (예제 기반). 한도를 낮춘 설정으로 실제 제한 동작을 검증한다."""

from __future__ import annotations

import pytest

from conftest import AUTH, capture_events, make_config
from todo_api.app import create_app

# 창 경계에서 카운터가 초기화되어 테스트가 흔들리지 않도록 시간 단위 창을 쓴다.


@pytest.fixture
def limited(tmp_path):
    def _make(default: str = "100 per hour", auth_failure: str = "100 per hour"):
        config = make_config(
            tmp_path,
            rate_limit_enabled=True,
            rate_limit_default=default,
            rate_limit_auth_failure=auth_failure,
        )
        return create_app(config).test_client()

    return _make


def test_requests_beyond_limit_get_429(limited):
    client = limited(default="5 per hour")
    with capture_events() as events:
        statuses = [client.get("/todos", headers=AUTH).status_code for _ in range(6)]

    assert statuses == [200] * 5 + [429]
    blocked = client.get("/todos", headers=AUTH)
    assert blocked.get_json()["error"]["code"] == "rate_limited"
    assert blocked.headers["Retry-After"] == "3600"
    assert events.named("rate_limited")[0]["path"] == "/todos"


def test_limit_is_shared_across_all_routes_including_health(limited):
    client = limited(default="5 per hour")
    for _ in range(3):
        assert client.get("/todos", headers=AUTH).status_code == 200
    for _ in range(2):
        assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429
    assert client.get("/todos", headers=AUTH).status_code == 429


def test_repeated_auth_failures_block_the_address_even_with_valid_key(limited):
    client = limited(auth_failure="3 per hour")
    statuses = [client.get("/todos").status_code for _ in range(4)]
    assert statuses == [401, 401, 401, 429]

    blocked = client.get("/todos", headers=AUTH)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "3600"
    # 공개 라우트는 인증 실패 한도의 영향을 받지 않는다.
    assert client.get("/health").status_code == 200


def test_successful_requests_do_not_consume_auth_failure_limit(limited):
    client = limited(auth_failure="3 per hour")
    for _ in range(10):
        assert client.get("/todos", headers=AUTH).status_code == 200
    assert client.get("/todos").status_code == 401


def test_failures_below_limit_do_not_block_valid_requests(limited):
    client = limited(auth_failure="3 per hour")
    for _ in range(2):
        assert client.get("/todos").status_code == 401
    assert client.get("/todos", headers=AUTH).status_code == 200


def test_default_limits_match_requirements(tmp_path):
    config = make_config(tmp_path, rate_limit_enabled=True)
    assert config.rate_limit_default == "60 per minute"
    assert config.rate_limit_auth_failure == "10 per minute"
    client = create_app(config).test_client()
    statuses = [client.get("/health").status_code for _ in range(61)]
    assert statuses.count(200) == 60
    assert statuses[-1] == 429
