"""저장소 계층 단위 테스트 (예제 기반)."""

from __future__ import annotations

import sqlite3

import pytest

from todo_api import repository
from todo_api.db import connect, init_db, write_transaction
from todo_api.errors import DuplicateTitle


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "data" / "todo.db"
    init_db(path, timeout=1.0)
    return path


@pytest.fixture
def conn(db_path):
    connection = connect(db_path, timeout=1.0)
    yield connection
    connection.close()


def count_rows(conn) -> int:
    return conn.execute("SELECT count(*) FROM todos").fetchone()[0]


def test_init_db_is_idempotent_and_enables_wal(db_path, conn):
    init_db(db_path, timeout=1.0)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    indexes = {row["name"] for row in conn.execute("PRAGMA index_list('todos')")}
    assert {"idx_todos_active_title", "idx_todos_active_created"} <= indexes


def test_create_returns_pending_todo_with_server_assigned_fields(conn):
    todo = repository.create_todo(conn, "우유 사기")
    assert todo.id == 1
    assert todo.completed is False
    assert repository.get_todo(conn, todo.id) == todo


def test_list_is_newest_first(conn):
    ids = [repository.create_todo(conn, title).id for title in ["a", "b", "c"]]
    assert [todo.id for todo in repository.list_todos(conn)] == ids[::-1]


def test_list_orders_by_id_when_timestamps_tie(conn, monkeypatch):
    monkeypatch.setattr(repository, "utc_now_iso", lambda: "2026-01-01T00:00:00.000000Z")
    ids = [repository.create_todo(conn, title).id for title in ["a", "b", "c"]]
    assert [todo.id for todo in repository.list_todos(conn)] == ids[::-1]


def test_list_filters_by_completion(conn):
    done = repository.create_todo(conn, "done")
    pending = repository.create_todo(conn, "pending")
    repository.set_completed(conn, done.id, True)
    assert [t.id for t in repository.list_todos(conn, completed=True)] == [done.id]
    assert [t.id for t in repository.list_todos(conn, completed=False)] == [pending.id]


def test_set_completed_reports_previous_value(conn):
    todo = repository.create_todo(conn, "a")
    updated, previous = repository.set_completed(conn, todo.id, True)
    assert (updated.completed, previous) == (True, False)
    updated, previous = repository.set_completed(conn, todo.id, True)
    assert (updated.completed, previous) == (True, True)
    assert repository.set_completed(conn, 999, True) == (None, None)


def test_completion_time_is_recorded_and_cleared(conn):
    todo = repository.create_todo(conn, "a")
    assert todo.completed_at is None

    done, _ = repository.set_completed(conn, todo.id, True)
    assert done.completed_at is not None
    assert done.completed_at >= todo.created_at
    assert repository.get_todo(conn, todo.id) == done

    again, _ = repository.set_completed(conn, todo.id, True)
    assert again.completed_at == done.completed_at

    undone, _ = repository.set_completed(conn, todo.id, False)
    assert undone.completed_at is None
    assert repository.get_todo(conn, todo.id) == undone


def test_soft_delete_keeps_row_but_hides_it(conn):
    todo = repository.create_todo(conn, "a")
    assert repository.soft_delete(conn, todo.id) is True
    assert repository.soft_delete(conn, todo.id) is False
    assert repository.get_todo(conn, todo.id) is None
    assert repository.list_todos(conn) == []
    assert repository.set_completed(conn, todo.id, True) == (None, None)
    assert count_rows(conn) == 1


def test_duplicate_title_ignores_ascii_case_only(conn):
    repository.create_todo(conn, "Buy Milk")
    with pytest.raises(DuplicateTitle):
        repository.create_todo(conn, "buy milk")
    # 영문 외 문자는 완전히 같을 때만 중복이다.
    repository.create_todo(conn, "École")
    repository.create_todo(conn, "école")
    assert count_rows(conn) == 3


def test_title_can_be_reused_after_delete(conn):
    first = repository.create_todo(conn, "a")
    repository.soft_delete(conn, first.id)
    second = repository.create_todo(conn, "A")
    assert second.id != first.id


def test_sql_in_title_is_stored_as_plain_data(conn):
    title = "x'); DROP TABLE todos; --"
    todo = repository.create_todo(conn, title)
    assert repository.get_todo(conn, todo.id).title == title
    assert count_rows(conn) == 1


def test_database_constraints_reject_invalid_rows(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO todos (title, created_at) VALUES ('', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO todos (title, completed, created_at) VALUES ('a', 2, 'x')"
        )


def test_write_transaction_rolls_back_on_error(conn):
    with pytest.raises(RuntimeError):
        with write_transaction(conn):
            conn.execute("INSERT INTO todos (title, created_at) VALUES ('a', 'x')")
            raise RuntimeError("실패")
    assert count_rows(conn) == 0
