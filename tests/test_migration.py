"""DB 이전 테스트: completed_at 열이 없던 이전 버전의 DB (예제 기반 + 속성 기반)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from conftest import AUTH, make_config
from strategies import unique_titles
from todo_api.app import create_app
from todo_api.db import connect, init_db

# 3차 워크플로까지의 스키마 (completed_at 없음)
OLD_SCHEMA = """
CREATE TABLE todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX idx_todos_active_title
    ON todos (title COLLATE NOCASE)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_todos_active_created
    ON todos (created_at DESC, id DESC)
    WHERE deleted_at IS NULL;
"""


def make_old_db(path: Path, rows: list[tuple[str, int, str, str | None]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(OLD_SCHEMA)
        with conn:
            conn.executemany(
                "INSERT INTO todos (title, completed, created_at, deleted_at)"
                " VALUES (?, ?, ?, ?)",
                rows,
            )
    finally:
        conn.close()


def columns(path: Path) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        return [row[1] for row in conn.execute("PRAGMA table_info(todos)")]
    finally:
        conn.close()


def dump(path: Path, names: str) -> list[tuple]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT {names} FROM todos ORDER BY id").fetchall()
    finally:
        conn.close()


OLD_ROWS = [
    ("우유 사기", 1, "2026-10-12T05:00:00.000000Z", None),
    ("책 반납", 0, "2026-10-12T06:00:00.000000Z", None),
    ("지운 항목", 1, "2026-10-12T07:00:00.000000Z", "2026-10-12T08:00:00.000000Z"),
]
OLD_COLUMNS = "id, title, completed, created_at, deleted_at"


def test_old_database_gains_the_column_and_keeps_its_data(tmp_path):
    path = tmp_path / "todo.db"
    make_old_db(path, OLD_ROWS)
    before = dump(path, OLD_COLUMNS)

    init_db(path, timeout=1.0)

    assert columns(path)[-1] == "completed_at"
    assert dump(path, OLD_COLUMNS) == before
    # 예전에 완료한 항목도 완료 시각은 알 수 없으므로 비어 있다.
    assert dump(path, "completed_at") == [(None,), (None,), (None,)]


def test_migration_runs_once_and_is_logged(tmp_path, events):
    path = tmp_path / "todo.db"
    make_old_db(path, OLD_ROWS)
    init_db(path, timeout=1.0)
    init_db(path, timeout=1.0)
    assert columns(path).count("completed_at") == 1
    assert len(events.named("db_migrated")) == 1


def test_new_database_already_has_the_column(tmp_path, events):
    path = tmp_path / "todo.db"
    init_db(path, timeout=1.0)
    assert "completed_at" in columns(path)
    assert events.named("db_migrated") == []


def test_api_on_migrated_database(tmp_path):
    path = tmp_path / "instance" / "todo.db"
    make_old_db(path, OLD_ROWS)
    client = create_app(make_config(tmp_path, db_path=path)).test_client()

    listed = client.get("/todos", headers=AUTH).get_json()["todos"]
    assert [(t["title"], t["completed"], t["completed_at"]) for t in listed] == [
        ("책 반납", False, None),
        ("우유 사기", True, None),
    ]
    done = client.patch("/todos/2", json={"completed": True}, headers=AUTH).get_json()
    assert done["completed_at"] is not None


def test_previous_code_can_still_read_the_migrated_database(tmp_path):
    """되돌리기(DNFR-01): 이전 버전이 쓰던 SQL이 새 열이 있어도 그대로 동작한다."""
    path = tmp_path / "todo.db"
    make_old_db(path, OLD_ROWS)
    init_db(path, timeout=1.0)
    conn = connect(path, timeout=1.0)
    try:
        with conn:
            conn.execute(
                "INSERT INTO todos (title, completed, created_at) VALUES (?, 0, ?)",
                ("새 항목", "2026-10-14T00:00:00.000000Z"),
            )
            conn.execute("UPDATE todos SET completed = ? WHERE id = ?", (0, 1))
        rows = conn.execute(
            "SELECT id, title, completed, created_at FROM todos WHERE deleted_at IS NULL"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 3


@settings(max_examples=30)
@given(
    titles=unique_titles(max_size=6),
    data=st.data(),
)
def test_property_migration_preserves_every_row(titles, data):
    """불변식(PBT-03): 이전 전후로 기존 열의 값이 모두 같고, 새 열은 모두 비어 있다."""
    rows = [
        (
            title,
            data.draw(st.sampled_from([0, 1])),
            f"2026-01-01T00:00:{index:02d}.000000Z",
            data.draw(st.sampled_from([None, "2026-02-01T00:00:00.000000Z"])),
        )
        for index, title in enumerate(titles)
    ]
    # 삭제되지 않은 행끼리만 제목 중복 금지가 적용된다(제너레이터가 이미 보장).
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "todo.db"
        make_old_db(path, rows)
        before = dump(path, OLD_COLUMNS)
        init_db(path, timeout=1.0)
        init_db(path, timeout=1.0)
        assert dump(path, OLD_COLUMNS) == before
        assert dump(path, "completed_at") == [(None,)] * len(rows)
