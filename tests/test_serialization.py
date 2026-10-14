"""직렬화 단위 테스트 (예제 기반)."""

from __future__ import annotations

import re

from todo_api.serialization import (
    Todo,
    todo_from_row,
    todo_to_dict,
    todo_to_row,
    utc_now_iso,
)

ROW = {
    "id": 3,
    "title": "우유 사기",
    "completed": 1,
    "created_at": "2026-10-12T05:00:00.000000Z",
    "completed_at": "2026-10-13T01:30:00.000000Z",
}


def test_row_is_converted_to_todo_with_boolean_flag():
    assert todo_from_row(ROW) == Todo(
        3, "우유 사기", True, "2026-10-12T05:00:00.000000Z", "2026-10-13T01:30:00.000000Z"
    )


def test_todo_is_converted_back_to_row():
    assert todo_to_row(todo_from_row(ROW)) == ROW


def test_api_representation_has_exactly_the_public_fields():
    row = {**ROW, "deleted_at": "2026-10-13T00:00:00.000000Z"}
    assert todo_to_dict(todo_from_row(row)) == {
        "id": 3,
        "title": "우유 사기",
        "completed": True,
        "created_at": "2026-10-12T05:00:00.000000Z",
        "completed_at": "2026-10-13T01:30:00.000000Z",
    }


def test_missing_completion_time_is_null_in_the_api():
    row = {**ROW, "completed_at": None}
    assert todo_to_dict(todo_from_row(row))["completed_at"] is None


def test_timestamps_are_fixed_width_utc_so_they_sort_chronologically():
    first, second = utc_now_iso(), utc_now_iso()
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z"
    assert re.fullmatch(pattern, first)
    assert first <= second
