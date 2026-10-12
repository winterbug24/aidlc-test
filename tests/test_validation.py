"""입력 검증 단위 테스트 (예제 기반)."""

from __future__ import annotations

import pytest

from todo_api.errors import ValidationError
from todo_api.validation import (
    CREATE_TODO_SCHEMA,
    LIST_QUERY_SCHEMA,
    UPDATE_TODO_SCHEMA,
    FieldError,
    normalize_title,
    parse_completed_flag,
    parse_completed_query,
    validate_object,
)


def details_of(exc_info) -> list[tuple[str, str]]:
    return [(d["field"], d["reason"]) for d in exc_info.value.details]


def test_normalize_title_strips_surrounding_whitespace():
    assert normalize_title("  우유 사기\n") == "우유 사기"


def test_normalize_title_keeps_html_characters_as_is():
    assert normalize_title("<b>a < b</b>") == "<b>a < b</b>"


@pytest.mark.parametrize("length", [1, 200])
def test_normalize_title_accepts_boundary_lengths(length):
    assert normalize_title("가" * length) == "가" * length


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (123, "invalid_type"),
        (True, "invalid_type"),
        (None, "invalid_type"),
        (["a"], "invalid_type"),
        ("", "too_short"),
        ("   \t\n", "too_short"),
        ("가" * 201, "too_long"),
        ("a\x00b", "invalid_characters"),
        ("줄\n바꿈", "invalid_characters"),
        ("a\ud800b", "invalid_characters"),
    ],
)
def test_normalize_title_rejects_invalid_values(value, reason):
    with pytest.raises(FieldError) as exc_info:
        normalize_title(value)
    assert exc_info.value.reason == reason


def test_length_is_checked_after_stripping():
    assert normalize_title(" " * 50 + "a" * 200 + " " * 50) == "a" * 200


@pytest.mark.parametrize("value", ["true", 1, 0, None, "false"])
def test_completed_flag_must_be_json_boolean(value):
    with pytest.raises(FieldError):
        parse_completed_flag(value)


def test_completed_query_accepts_only_lowercase_true_false():
    assert parse_completed_query("true") is True
    assert parse_completed_query("false") is False
    for value in ["True", "1", "yes", "", ["true", "false"]]:
        with pytest.raises(FieldError):
            parse_completed_query(value)


def test_validate_object_returns_normalized_values():
    assert validate_object({"title": " a "}, CREATE_TODO_SCHEMA) == {"title": "a"}
    assert validate_object({"completed": True}, UPDATE_TODO_SCHEMA) == {"completed": True}
    assert validate_object({}, LIST_QUERY_SCHEMA) == {}


@pytest.mark.parametrize("data", [None, [], "text", 1])
def test_validate_object_rejects_non_objects(data):
    with pytest.raises(ValidationError) as exc_info:
        validate_object(data, CREATE_TODO_SCHEMA)
    assert details_of(exc_info) == [("body", "invalid_type")]


def test_validate_object_reports_missing_required_field():
    with pytest.raises(ValidationError) as exc_info:
        validate_object({}, CREATE_TODO_SCHEMA)
    assert details_of(exc_info) == [("title", "required")]


def test_validate_object_reports_every_problem_at_once():
    with pytest.raises(ValidationError) as exc_info:
        validate_object({"title": "", "priority": 1, "due": "x"}, CREATE_TODO_SCHEMA)
    assert details_of(exc_info) == [
        ("due", "unknown_field"),
        ("priority", "unknown_field"),
        ("title", "too_short"),
    ]
