"""SQLite 연결 관리: 요청 단위 연결, 스키마 초기화, 잠금 시 재시도."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from flask import current_app, g

from todo_api.config import create_private_file, ensure_private_dir
from todo_api.errors import ServiceUnavailable
from todo_api.logging_setup import log_event

T = TypeVar("T")

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_todos_active_title
    ON todos (title COLLATE NOCASE)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_todos_active_created
    ON todos (created_at DESC, id DESC)
    WHERE deleted_at IS NULL;
"""

RETRY_AFTER_SECONDS = "5"
_LOCK_ERROR_CODES = (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)


def connect(db_path: Path, timeout: float) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path, timeout: float) -> None:
    """DB 파일, 스키마, 인덱스를 없으면 만든다. 여러 번 실행해도 안전하다."""
    ensure_private_dir(db_path.parent)
    create_private_file(db_path)
    conn = connect(db_path, timeout)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def get_db() -> sqlite3.Connection:
    """현재 요청의 연결. 처음 필요할 때 연다."""
    if "db" not in g:
        config = current_app.config["TODO_CONFIG"]
        g.db = connect(config.db_path, config.db_timeout_seconds)
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def write_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """쓰기 잠금을 먼저 잡아 읽고 쓰는 사이에 다른 쓰기가 끼어들지 못하게 한다."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


def is_locked_error(exc: sqlite3.OperationalError) -> bool:
    code = getattr(exc, "sqlite_errorcode", None)
    if code is not None:
        return (code & 0xFF) in _LOCK_ERROR_CODES
    message = str(exc).lower()
    return "locked" in message or "busy" in message


def run_with_retry(operation: str, func: Callable[[], T]) -> T:
    """잠금으로 실패하면 한 번만 다시 시도하고, 또 실패하면 503으로 알린다."""
    try:
        return func()
    except sqlite3.OperationalError as exc:
        if not is_locked_error(exc):
            raise
        log_event(
            "db_retry",
            "DB 잠금으로 재시도",
            level=logging.WARNING,
            operation=operation,
        )
    try:
        return func()
    except sqlite3.OperationalError as exc:
        if not is_locked_error(exc):
            raise
        raise ServiceUnavailable(headers={"Retry-After": RETRY_AFTER_SECONDS}) from exc
