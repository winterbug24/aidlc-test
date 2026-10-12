"""화면 파일 제공 테스트 (예제 기반)."""

from __future__ import annotations

import re

import pytest

from conftest import AUTH, TEST_API_KEY
from todo_api.routes.web import ASSETS, INDEX, WEB_DIR

SERVED_FILES = [
    ("/api_test", "text/html; charset=utf-8"),
    ("/api_test/", "text/html; charset=utf-8"),
    ("/api_test/app.css", "text/css; charset=utf-8"),
    ("/api_test/app.js", "text/javascript; charset=utf-8"),
]


@pytest.mark.parametrize(("path", "content_type"), SERVED_FILES)
def test_screen_files_are_served_without_authentication(client, path, content_type):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == content_type
    assert response.get_data()


def test_both_index_addresses_return_the_same_document(client):
    assert client.get("/api_test").get_data() == client.get("/api_test/").get_data()


@pytest.mark.parametrize(
    "path",
    [
        "/api_test/index.html",
        "/api_test/missing.js",
        "/api_test/app.js.map",
        "/api_test/../config.py",
        "/api_test/..%2fconfig.py",
        "/api_test/%2e%2e/app.py",
        "/api_test/..%5capp.py",
        "/api_test/web/app.js",
        "/api_test/app.js/extra",
        "/api_test//etc/passwd",
        "/api_test/.env",
        "/static/app.js",
        "/app.js",
        "/",
    ],
)
def test_anything_outside_the_fixed_list_is_not_served(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_only_get_is_allowed_on_screen_routes(client):
    assert client.post("/api_test").status_code == 405
    assert client.delete("/api_test/app.js").status_code == 405


def test_serving_the_screen_does_not_open_the_api(client, create):
    create("비공개 항목")
    assert client.get("/api_test").status_code == 200
    assert client.get("/todos").status_code == 401
    assert client.get("/todos/1").status_code == 401


def test_screen_files_contain_neither_data_nor_key(client, create):
    create("비공개 항목")
    for path, _ in SERVED_FILES:
        text = client.get(path).get_data(as_text=True)
        assert "비공개 항목" not in text
        assert TEST_API_KEY not in text


def test_document_loads_only_same_origin_files_and_has_no_inline_code(client):
    html = client.get("/api_test").get_data(as_text=True)
    assert '<html lang="ko">' in html
    assert re.findall(r'<script[^>]*\bsrc="([^"]+)"', html) == ["/api_test/app.js"]
    assert re.findall(r'<link rel="stylesheet" href="([^"]+)"', html) == ["/api_test/app.css"]
    # 인라인 스크립트, 인라인 스타일, 인라인 이벤트 처리기가 없어야 정책과 맞는다.
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert "<style" not in html
    assert not re.search(r"\sstyle=", html)
    assert not re.search(r"\son[a-z]+=", html)
    assert not re.search(r"https?://", html)
    # 브라우저가 아이콘 파일을 따로 요청하지 않게 한다.
    assert '<link rel="icon" href="data:,">' in html


def test_script_never_builds_markup_from_strings(client):
    script = client.get("/api_test/app.js").get_data(as_text=True)
    for forbidden in ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("]:
        assert forbidden not in script
    assert "console." not in script
    assert not re.search(r"https?://", script)


def test_screen_files_stay_small():
    names = [INDEX[0], *(filename for filename, _ in ASSETS.values())]
    total = sum((WEB_DIR / name).stat().st_size for name in names)
    assert total <= 60 * 1024


def test_screen_requests_are_logged_like_any_other_request(client, events):
    client.get("/api_test")
    logged = events.named("request")
    assert logged[0]["path"] == "/api_test"
    assert logged[0]["status"] == 200


def test_existing_api_still_works_alongside_the_screen(client, create):
    todo = create("a")
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": [todo]}
