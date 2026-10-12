"""저장소 행과 Todo 표현 사이의 변환."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Todo:
    id: int
    title: str
    completed: bool
    created_at: str


def utc_now_iso() -> str:
    """UTC 현재 시각. 문자열 정렬 순서가 시간 순서와 같도록 자릿수를 고정한다."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def todo_from_row(row: Mapping[str, Any]) -> Todo:
    return Todo(
        id=row["id"],
        title=row["title"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
    )


def todo_to_row(todo: Todo) -> dict[str, Any]:
    return {
        "id": todo.id,
        "title": todo.title,
        "completed": int(todo.completed),
        "created_at": todo.created_at,
    }


def todo_to_dict(todo: Todo) -> dict[str, Any]:
    """API 응답 표현. deleted_at은 노출하지 않는다."""
    return {
        "id": todo.id,
        "title": todo.title,
        "completed": todo.completed,
        "created_at": todo.created_at,
    }
