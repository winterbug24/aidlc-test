"""속성 기반 테스트 (Hypothesis). 예제 기반 테스트는 다른 파일에 있다.

속성 번호(P-01~P-09)는 기능 설계 business-logic-model.md 6장을 따른다.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from conftest import AUTH, fresh_client, make_config
from strategies import (
    ascii_fold,
    ascii_swapcase,
    invalid_titles,
    padded_titles,
    todos,
    unique_titles,
    valid_titles,
)
from todo_api.app import create_app
from todo_api.serialization import todo_from_row, todo_to_dict, todo_to_row
from todo_api.validation import FieldError, normalize_title

# 예제마다 앱과 DB를 새로 만들기 때문에 예제 수를 줄인다.
api_settings = settings(max_examples=30)


def list_todos(client, query: str = "") -> list[dict]:
    response = client.get(f"/todos{query}", headers=AUTH)
    assert response.status_code == 200
    return response.get_json()["todos"]


def create(client, title: str) -> dict:
    response = client.post("/todos", json={"title": title}, headers=AUTH)
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


# --- 순수 함수 속성 ---


@given(padded_titles())
def test_normalize_title_returns_core_and_is_idempotent(pair):
    raw, core = pair
    assert normalize_title(raw) == core
    assert normalize_title(normalize_title(raw)) == core


@given(invalid_titles())
def test_normalize_title_rejects_every_invalid_title(title):
    with pytest.raises(FieldError):
        normalize_title(title)


@given(todos())
def test_p02_todo_survives_row_and_json_round_trips(todo):
    assert todo_from_row(todo_to_row(todo)) == todo
    representation = todo_to_dict(todo)
    assert json.loads(json.dumps(representation)) == representation


# --- API 속성 ---


@api_settings
@given(padded_titles())
def test_p01_created_title_reads_back_as_stripped_input(pair):
    raw, core = pair
    with fresh_client() as client:
        created = create(client, raw)
        fetched = client.get(f"/todos/{created['id']}", headers=AUTH).get_json()
    assert created["title"] == core
    assert fetched == created


@api_settings
@given(st.lists(st.tuples(st.booleans(), st.booleans()), max_size=8), st.data())
def test_p03_p04_p05_list_invariants(flags, data):
    titles = data.draw(st.lists(valid_titles(), unique_by=ascii_fold, min_size=len(flags), max_size=len(flags)))
    with fresh_client() as client:
        deleted_ids = set()
        for title, (completed, deleted) in zip(titles, flags):
            todo = create(client, title)
            if completed:
                client.patch(f"/todos/{todo['id']}", json={"completed": True}, headers=AUTH)
            if deleted:
                client.delete(f"/todos/{todo['id']}", headers=AUTH)
                deleted_ids.add(todo["id"])

        everything = list_todos(client)
        done = list_todos(client, "?completed=true")
        pending = list_todos(client, "?completed=false")
        deleted_statuses = {
            client.get(f"/todos/{todo_id}", headers=AUTH).status_code for todo_id in deleted_ids
        }

    # P-03: 필터 결과는 모두 요청한 완료 상태이고, 둘을 합치면 전체와 같다.
    assert all(todo["completed"] is True for todo in done)
    assert all(todo["completed"] is False for todo in pending)
    assert sorted(t["id"] for t in done + pending) == sorted(t["id"] for t in everything)
    # P-04: 삭제한 항목은 목록에도 단건 조회에도 나타나지 않는다.
    assert deleted_ids.isdisjoint(todo["id"] for todo in everything)
    assert deleted_statuses <= {404}
    assert len(everything) == len(flags) - len(deleted_ids)
    # P-05: 목록은 항상 최신 순이다.
    for listing in (everything, done, pending):
        keys = [(todo["created_at"], todo["id"]) for todo in listing]
        assert keys == sorted(keys, reverse=True)


@api_settings
@given(valid_titles())
def test_p06_ascii_case_variant_of_active_title_is_rejected(title):
    with fresh_client() as client:
        create(client, title)
        response = client.post("/todos", json={"title": ascii_swapcase(title)}, headers=AUTH)
        remaining = list_todos(client)
    assert response.status_code == 409
    assert [todo["title"] for todo in remaining] == [title]


@api_settings
@given(unique_titles(max_size=3), invalid_titles())
def test_p07_invalid_title_is_rejected_and_changes_nothing(existing, invalid):
    with fresh_client() as client:
        for title in existing:
            create(client, title)
        before = list_todos(client)
        response = client.post("/todos", json={"title": invalid}, headers=AUTH)
        after = list_todos(client)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"
    assert after == before


@api_settings
@given(valid_titles(), st.booleans(), st.booleans())
def test_p08_setting_completed_twice_equals_setting_it_once(title, initial, target):
    with fresh_client() as client:
        todo = create(client, title)
        url = f"/todos/{todo['id']}"
        client.patch(url, json={"completed": initial}, headers=AUTH)
        once = client.patch(url, json={"completed": target}, headers=AUTH).get_json()
        twice = client.patch(url, json={"completed": target}, headers=AUTH).get_json()
        stored = client.get(url, headers=AUTH).get_json()
    assert once == twice == stored
    assert stored["completed"] is target


# --- P-09: 상태 기반 모델 테스트 ---

# 중복 충돌이 자주 일어나도록 대소문자만 다른 제목을 섞는다.
machine_titles = st.one_of(
    st.sampled_from(["Task", "task", "TASK", "할 일", "École", "école"]),
    valid_titles(),
)


class TodoApiMachine(RuleBasedStateMachine):
    """임의의 추가/변경/삭제 순서를 메모리 모델과 실제 API에 함께 적용한다."""

    def __init__(self) -> None:
        super().__init__()
        self._tmp = tempfile.TemporaryDirectory()
        self.client = create_app(make_config(Path(self._tmp.name))).test_client()
        self.active: dict[int, dict] = {}
        self.known_ids: list[int] = []

    def teardown(self) -> None:
        self._tmp.cleanup()

    def _pick(self, index: int) -> int:
        return self.known_ids[index % len(self.known_ids)]

    @rule(title=machine_titles)
    def add(self, title):
        response = self.client.post("/todos", json={"title": title}, headers=AUTH)
        folded = ascii_fold(title)
        if any(ascii_fold(todo["title"]) == folded for todo in self.active.values()):
            assert response.status_code == 409
            return
        assert response.status_code == 201
        todo = response.get_json()
        assert todo["title"] == title
        assert todo["completed"] is False
        assert todo["id"] not in self.known_ids
        self.active[todo["id"]] = todo
        self.known_ids.append(todo["id"])

    @precondition(lambda self: self.known_ids)
    @rule(index=st.integers(min_value=0), completed=st.booleans())
    def set_completed(self, index, completed):
        todo_id = self._pick(index)
        response = self.client.patch(
            f"/todos/{todo_id}", json={"completed": completed}, headers=AUTH
        )
        if todo_id not in self.active:
            assert response.status_code == 404
            return
        assert response.status_code == 200
        self.active[todo_id] = {**self.active[todo_id], "completed": completed}
        assert response.get_json() == self.active[todo_id]

    @precondition(lambda self: self.known_ids)
    @rule(index=st.integers(min_value=0))
    def delete(self, index):
        todo_id = self._pick(index)
        response = self.client.delete(f"/todos/{todo_id}", headers=AUTH)
        if todo_id not in self.active:
            assert response.status_code == 404
            return
        assert response.status_code == 204
        del self.active[todo_id]

    @invariant()
    def api_matches_model(self):
        expected = sorted(
            self.active.values(),
            key=lambda todo: (todo["created_at"], todo["id"]),
            reverse=True,
        )
        assert list_todos(self.client) == expected
        for flag in (True, False):
            query = f"?completed={'true' if flag else 'false'}"
            assert list_todos(self.client, query) == [
                todo for todo in expected if todo["completed"] is flag
            ]

    @invariant()
    def active_titles_are_unique_ignoring_ascii_case(self):
        folded = [ascii_fold(todo["title"]) for todo in list_todos(self.client)]
        assert len(folded) == len(set(folded))


TestTodoApiMachine = TodoApiMachine.TestCase
TestTodoApiMachine.settings = settings(max_examples=25, stateful_step_count=20)
