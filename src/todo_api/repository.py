"""Todo 저장소. SQL은 이 모듈과 db 모듈에만 둔다.

모든 값은 자리표시자로 바인딩하고, 조회는 항상 삭제되지 않은 행만 대상으로 한다.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from todo_api.db import write_transaction
from todo_api.errors import DuplicateTitle
from todo_api.serialization import Todo, todo_from_row, utc_now_iso

_COLUMNS = "id, title, completed, created_at, completed_at"


def create_todo(conn: sqlite3.Connection, title: str) -> Todo:
    created_at = utc_now_iso()
    try:
        with write_transaction(conn):
            cursor = conn.execute(
                "INSERT INTO todos (title, completed, created_at) VALUES (?, 0, ?)",
                (title, created_at),
            )
    except sqlite3.IntegrityError as exc:
        # 중복 판정을 유일 인덱스에 맡겨 동시 요청에도 안전하게 한다.
        if getattr(exc, "sqlite_errorname", "") == "SQLITE_CONSTRAINT_UNIQUE":
            raise DuplicateTitle() from exc
        raise
    return Todo(id=cursor.lastrowid, title=title, completed=False, created_at=created_at)


def list_todos(conn: sqlite3.Connection, completed: bool | None = None) -> list[Todo]:
    sql = f"SELECT {_COLUMNS} FROM todos WHERE deleted_at IS NULL"
    params: tuple[int, ...] = ()
    if completed is not None:
        sql += " AND completed = ?"
        params = (int(completed),)
    sql += " ORDER BY created_at DESC, id DESC"
    return [todo_from_row(row) for row in conn.execute(sql, params)]


def get_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM todos WHERE id = ? AND deleted_at IS NULL",
        (todo_id,),
    ).fetchone()
    return todo_from_row(row) if row else None


def set_completed(
    conn: sqlite3.Connection, todo_id: int, completed: bool
) -> tuple[Todo | None, bool | None]:
    """완료 여부를 설정한다. (현재 Todo, 변경 전 값)을 돌려주며 대상이 없으면 (None, None).

    값이 바뀔 때만 완료 시각을 기록하거나(완료) 지운다(해제). 같은 값을 다시 보내면 그대로 둔다.
    """
    with write_transaction(conn):
        current = get_todo(conn, todo_id)
        if current is None:
            return None, None
        if current.completed == completed:
            return current, current.completed
        completed_at = utc_now_iso() if completed else None
        conn.execute(
            "UPDATE todos SET completed = ?, completed_at = ?"
            " WHERE id = ? AND deleted_at IS NULL",
            (int(completed), completed_at, todo_id),
        )
    updated = replace(current, completed=completed, completed_at=completed_at)
    return updated, current.completed


def soft_delete(conn: sqlite3.Connection, todo_id: int) -> bool:
    """삭제 시각을 기록한다. 대상이 없거나 이미 삭제되었으면 False."""
    with write_transaction(conn):
        cursor = conn.execute(
            "UPDATE todos SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (utc_now_iso(), todo_id),
        )
    return cursor.rowcount == 1
