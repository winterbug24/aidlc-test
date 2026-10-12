"""할 일 엔드포인트 테스트 (예제 기반): 엔드포인트별 정상/오류 케이스."""

from __future__ import annotations

import re
import sqlite3

import pytest

from conftest import AUTH


def error_of(response) -> dict:
    return response.get_json()["error"]


def reasons_of(response) -> list[tuple[str, str]]:
    return [(d["field"], d["reason"]) for d in error_of(response)["details"]]


# --- 추가 (FR-01) ---


def test_create_returns_201_with_pending_todo(client):
    response = client.post("/todos", json={"title": "우유 사기"}, headers=AUTH)
    assert response.status_code == 201
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert set(body) == {"id", "title", "completed", "created_at"}
    assert (body["id"], body["title"], body["completed"]) == (1, "우유 사기", False)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", body["created_at"])


def test_create_strips_surrounding_whitespace(create):
    assert create("  책 반납  ")["title"] == "책 반납"


def test_create_accepts_200_characters(create):
    assert len(create("가" * 200)["title"]) == 200


def test_create_stores_html_characters_as_is(client, create):
    title = "<script>alert('x')</script> a < b"
    todo = create(title)
    fetched = client.get(f"/todos/{todo['id']}", headers=AUTH)
    assert fetched.get_json()["title"] == title
    assert fetched.mimetype == "application/json"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({}, [("title", "required")]),
        ({"title": 123}, [("title", "invalid_type")]),
        ({"title": None}, [("title", "invalid_type")]),
        ({"title": ""}, [("title", "too_short")]),
        ({"title": "   "}, [("title", "too_short")]),
        ({"title": "가" * 201}, [("title", "too_long")]),
        ({"title": "a\x00b"}, [("title", "invalid_characters")]),
        ({"title": "a\nb"}, [("title", "invalid_characters")]),
        ({"title": "a", "priority": 1}, [("priority", "unknown_field")]),
        (["a"], [("body", "invalid_type")]),
        ("a", [("body", "invalid_type")]),
    ],
)
def test_create_rejects_invalid_body(client, body, expected):
    response = client.post("/todos", json=body, headers=AUTH)
    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert reasons_of(response) == expected
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": []}


def test_create_rejects_malformed_json(client):
    response = client.post(
        "/todos", data="{not json", content_type="application/json", headers=AUTH
    )
    assert response.status_code == 400
    assert reasons_of(response) == [("body", "invalid_json")]


def test_create_rejects_non_json_content_type(client):
    response = client.post("/todos", data="title=a", content_type="text/plain", headers=AUTH)
    assert response.status_code == 415
    assert error_of(response)["code"] == "unsupported_media_type"


def test_create_rejects_duplicate_title_ignoring_ascii_case(client, create):
    create("Buy Milk")
    response = client.post("/todos", json={"title": " buy milk "}, headers=AUTH)
    assert response.status_code == 409
    assert error_of(response)["code"] == "duplicate_title"


def test_completed_todo_still_blocks_duplicate(client, create):
    todo = create("a")
    client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
    assert client.post("/todos", json={"title": "A"}, headers=AUTH).status_code == 409


def test_non_ascii_case_variants_are_different_titles(create):
    assert create("École")["id"] != create("école")["id"]


def test_title_can_be_registered_again_after_delete(client, create):
    first = create("a")
    client.delete(f"/todos/{first['id']}", headers=AUTH)
    assert create("a")["id"] != first["id"]


# --- 목록 조회 (FR-02) ---


def test_list_is_empty_initially(client):
    response = client.get("/todos", headers=AUTH)
    assert response.status_code == 200
    assert response.get_json() == {"todos": []}


def test_list_is_newest_first(client, create):
    created = [create(title) for title in ["a", "b", "c"]]
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": created[::-1]}


def test_list_filters_by_completion(client, create):
    done, pending = create("done"), create("pending")
    client.patch(f"/todos/{done['id']}", json={"completed": True}, headers=AUTH)

    completed = client.get("/todos?completed=true", headers=AUTH).get_json()["todos"]
    not_completed = client.get("/todos?completed=false", headers=AUTH).get_json()["todos"]
    assert [t["id"] for t in completed] == [done["id"]]
    assert [t["id"] for t in not_completed] == [pending["id"]]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("completed=yes", [("completed", "invalid_value")]),
        ("completed=True", [("completed", "invalid_value")]),
        ("completed=", [("completed", "invalid_value")]),
        ("completed=true&completed=false", [("completed", "invalid_value")]),
        ("limit=10", [("limit", "unknown_field")]),
    ],
)
def test_list_rejects_invalid_query(client, query, expected):
    response = client.get(f"/todos?{query}", headers=AUTH)
    assert response.status_code == 400
    assert reasons_of(response) == expected


def test_list_excludes_deleted(client, create):
    kept, removed = create("kept"), create("removed")
    client.delete(f"/todos/{removed['id']}", headers=AUTH)
    assert client.get("/todos", headers=AUTH).get_json() == {"todos": [kept]}


# --- 단건 조회 (FR-03) ---


def test_get_returns_todo(client, create):
    todo = create("a")
    response = client.get(f"/todos/{todo['id']}", headers=AUTH)
    assert response.status_code == 200
    assert response.get_json() == todo


@pytest.mark.parametrize("path", ["/todos/999", "/todos/0", "/todos/abc", "/todos/-1"])
def test_get_unknown_id_is_404(client, path):
    response = client.get(path, headers=AUTH)
    assert response.status_code == 404
    assert error_of(response)["code"] == "not_found"


def test_get_id_beyond_database_range_is_404(client):
    assert client.get(f"/todos/{2**63}", headers=AUTH).status_code == 404
    assert client.get(f"/todos/{10**40}", headers=AUTH).status_code == 404


def test_get_deleted_is_404(client, create):
    todo = create("a")
    client.delete(f"/todos/{todo['id']}", headers=AUTH)
    assert client.get(f"/todos/{todo['id']}", headers=AUTH).status_code == 404


# --- 완료 상태 변경 (FR-04) ---


def test_patch_sets_and_unsets_completed(client, create):
    todo = create("a")
    done = client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
    assert done.status_code == 200
    assert done.get_json() == {**todo, "completed": True}

    undone = client.patch(f"/todos/{todo['id']}", json={"completed": False}, headers=AUTH)
    assert undone.get_json() == todo
    assert client.get(f"/todos/{todo['id']}", headers=AUTH).get_json() == todo


def test_patch_same_value_is_idempotent(client, create, events):
    todo = create("a")
    first = client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
    second = client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
    assert first.get_json() == second.get_json()
    # 실제로 바뀐 경우에만 변경 이벤트를 남긴다.
    assert events.named("todo_completion_changed") == [
        {"id": todo["id"], "before": False, "after": True}
    ]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({}, [("completed", "required")]),
        ({"completed": "true"}, [("completed", "invalid_type")]),
        ({"completed": 1}, [("completed", "invalid_type")]),
        ({"completed": None}, [("completed", "invalid_type")]),
        ({"completed": True, "title": "new"}, [("title", "unknown_field")]),
    ],
)
def test_patch_rejects_invalid_body(client, create, body, expected):
    todo = create("a")
    response = client.patch(f"/todos/{todo['id']}", json=body, headers=AUTH)
    assert response.status_code == 400
    assert reasons_of(response) == expected
    assert client.get(f"/todos/{todo['id']}", headers=AUTH).get_json() == todo


def test_patch_unknown_or_deleted_is_404(client, create):
    assert client.patch("/todos/999", json={"completed": True}, headers=AUTH).status_code == 404
    todo = create("a")
    client.delete(f"/todos/{todo['id']}", headers=AUTH)
    response = client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
    assert response.status_code == 404


# --- 삭제 (FR-05) ---


def test_delete_returns_204_without_body(client, create):
    todo = create("a")
    response = client.delete(f"/todos/{todo['id']}", headers=AUTH)
    assert response.status_code == 204
    assert response.get_data() == b""


def test_delete_twice_or_unknown_is_404(client, create):
    todo = create("a")
    client.delete(f"/todos/{todo['id']}", headers=AUTH)
    assert client.delete(f"/todos/{todo['id']}", headers=AUTH).status_code == 404
    assert client.delete("/todos/999", headers=AUTH).status_code == 404


def test_delete_is_logical_and_row_remains_in_database(client, create, config):
    todo = create("a")
    client.delete(f"/todos/{todo['id']}", headers=AUTH)
    conn = sqlite3.connect(config.db_path)
    try:
        row = conn.execute("SELECT title, deleted_at FROM todos").fetchone()
    finally:
        conn.close()
    assert row[0] == "a"
    assert row[1] is not None


# --- 변경 기록 ---


def test_changes_are_logged_without_title_text(client, create, events):
    todo = create("비밀스러운 제목")
    client.delete(f"/todos/{todo['id']}", headers=AUTH)
    assert events.named("todo_created") == [{"id": todo["id"]}]
    assert events.named("todo_deleted") == [{"id": todo["id"]}]
    logged = " ".join(f"{r.getMessage()} {r.fields}" for r in events.records)
    assert "비밀스러운 제목" not in logged
