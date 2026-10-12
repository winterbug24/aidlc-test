"""할 일 엔드포인트. 이 묶음의 모든 라우트는 API 키가 필요하다."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

from todo_api import repository
from todo_api.auth import require_api_key
from todo_api.db import get_db, run_with_retry
from todo_api.errors import NotFound, UnsupportedMediaType, ValidationError
from todo_api.logging_setup import log_event
from todo_api.serialization import todo_to_dict
from todo_api.validation import (
    CREATE_TODO_SCHEMA,
    LIST_QUERY_SCHEMA,
    UPDATE_TODO_SCHEMA,
    FieldSpec,
    validate_object,
)

bp = Blueprint("todos", __name__, url_prefix="/todos")
# 기본 거부: 묶음 전체에 인증을 걸어 라우트를 추가해도 자동으로 보호된다.
bp.before_request(require_api_key)

_MAX_SQLITE_INTEGER = 2**63 - 1


def _validated_body(schema: Mapping[str, FieldSpec]) -> dict[str, Any]:
    if not request.is_json:
        raise UnsupportedMediaType()
    try:
        data = request.get_json()
    except (BadRequest, RecursionError) as exc:
        raise ValidationError(
            "요청 본문이 올바른 JSON이 아닙니다.",
            details=[{"field": "body", "reason": "invalid_json"}],
        ) from exc
    return validate_object(data, schema)


def _validated_query(schema: Mapping[str, FieldSpec]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key in request.args:
        values = request.args.getlist(key)
        # 같은 파라미터가 여러 번 오면 목록으로 넘겨 검증에서 거부되게 한다.
        params[key] = values[0] if len(values) == 1 else values
    return validate_object(params, schema)


def _check_id(todo_id: int) -> int:
    if not 1 <= todo_id <= _MAX_SQLITE_INTEGER:
        raise NotFound()
    return todo_id


@bp.post("")
def create_todo():
    data = _validated_body(CREATE_TODO_SCHEMA)
    todo = run_with_retry(
        "create_todo", lambda: repository.create_todo(get_db(), data["title"])
    )
    log_event("todo_created", "할 일 생성", id=todo.id)
    return jsonify(todo_to_dict(todo)), 201


@bp.get("")
def list_todos():
    query = _validated_query(LIST_QUERY_SCHEMA)
    todos = run_with_retry(
        "list_todos", lambda: repository.list_todos(get_db(), query.get("completed"))
    )
    return jsonify({"todos": [todo_to_dict(todo) for todo in todos]})


@bp.get("/<int:todo_id>")
def get_todo(todo_id: int):
    _check_id(todo_id)
    todo = run_with_retry("get_todo", lambda: repository.get_todo(get_db(), todo_id))
    if todo is None:
        raise NotFound()
    return jsonify(todo_to_dict(todo))


@bp.patch("/<int:todo_id>")
def update_todo(todo_id: int):
    data = _validated_body(UPDATE_TODO_SCHEMA)
    _check_id(todo_id)
    todo, previous = run_with_retry(
        "set_completed",
        lambda: repository.set_completed(get_db(), todo_id, data["completed"]),
    )
    if todo is None:
        raise NotFound()
    if previous != todo.completed:
        log_event(
            "todo_completion_changed",
            "할 일 완료 상태 변경",
            id=todo.id,
            before=previous,
            after=todo.completed,
        )
    return jsonify(todo_to_dict(todo))


@bp.delete("/<int:todo_id>")
def delete_todo(todo_id: int):
    _check_id(todo_id)
    deleted = run_with_retry(
        "soft_delete", lambda: repository.soft_delete(get_db(), todo_id)
    )
    if not deleted:
        raise NotFound()
    log_event("todo_deleted", "할 일 삭제", id=todo_id)
    return "", 204
