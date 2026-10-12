"""DB 백업과 복원: python -m todo_api.backup {backup,restore,list}

앱과 독립적으로 실행한다. WAL 보조 파일이 있으므로 DB 파일을 직접 복사하지 말고
이 도구를 사용한다.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from todo_api.config import Config, create_private_file, ensure_private_dir

BACKUP_PREFIX = "todo-"
BACKUP_SUFFIX = ".db"
DEFAULT_KEEP = 7
_SIDECAR_SUFFIXES = ("-wal", "-shm")


class BackupError(RuntimeError):
    """백업 또는 복원을 수행할 수 없음."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _copy_database(source: Path, destination: Path) -> None:
    """SQLite 온라인 백업으로 일관된 사본을 만든다. 서버 실행 중에도 안전하다."""
    create_private_file(destination)
    src = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(destination))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def verify_database(path: Path) -> bool:
    """무결성 검사를 통과하고 todos 테이블이 있는 DB인지 확인한다."""
    if not path.is_file():
        return False
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'todos'"
            ).fetchone()
            return table is not None
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def list_backups(backup_dir: Path) -> list[Path]:
    """백업 파일을 오래된 것부터 돌려준다."""
    if not backup_dir.is_dir():
        return []
    return sorted(backup_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))


def backup_database(db_path: Path, backup_dir: Path, keep: int = DEFAULT_KEEP) -> Path:
    if not db_path.is_file():
        raise BackupError(f"DB 파일이 없습니다: {db_path}")
    ensure_private_dir(backup_dir)
    destination = backup_dir / f"{BACKUP_PREFIX}{_timestamp()}{BACKUP_SUFFIX}"
    try:
        _copy_database(db_path, destination)
    except sqlite3.Error as exc:
        destination.unlink(missing_ok=True)
        raise BackupError(f"백업에 실패했습니다: {exc}") from exc
    if not verify_database(destination):
        destination.unlink(missing_ok=True)
        raise BackupError("백업 사본이 무결성 검사를 통과하지 못했습니다.")
    for old in list_backups(backup_dir)[:-keep]:
        old.unlink()
    return destination


def restore_database(backup_path: Path, db_path: Path) -> Path | None:
    """백업으로 DB를 교체한다. 서버를 중지한 상태에서 실행해야 한다.

    기존 DB가 있으면 안전 사본을 남기고 그 경로를 돌려준다.
    """
    if not verify_database(backup_path):
        raise BackupError(f"올바른 백업 파일이 아닙니다: {backup_path}")
    ensure_private_dir(db_path.parent)

    safety_copy: Path | None = None
    if db_path.is_file():
        safety_copy = db_path.with_name(f"{db_path.name}.before-restore-{_timestamp()}")
        try:
            _copy_database(db_path, safety_copy)
        except sqlite3.Error:
            # 현재 DB가 손상되어 읽을 수 없으면 파일 그대로 보존한다.
            shutil.copy2(db_path, safety_copy)
            os.chmod(safety_copy, 0o600)

    staging = db_path.with_name(f"{db_path.name}.restoring")
    try:
        _copy_database(backup_path, staging)
        for suffix in _SIDECAR_SUFFIXES:
            db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)
        os.replace(staging, db_path)
    finally:
        staging.unlink(missing_ok=True)
    return safety_copy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="할 일 DB 백업/복원 도구")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("backup", help="백업을 만들고 최근 것만 보관")
    commands.add_parser("list", help="백업 목록 표시")
    restore = commands.add_parser("restore", help="백업으로 DB 교체 (서버 중지 후 실행)")
    restore.add_argument("backup_file", type=Path)
    args = parser.parse_args(argv)

    # 백업 도구는 API 키를 쓰지 않는다. 경로 설정만 읽도록 키 자리를 채워 넘긴다.
    config = Config.from_env({**os.environ, "TODO_API_KEY": "-" * 32})

    try:
        if args.command == "backup":
            path = backup_database(config.db_path, config.backup_dir, config.backup_keep)
            print(f"백업 완료: {path}")
        elif args.command == "list":
            for path in list_backups(config.backup_dir):
                print(path)
        else:
            safety_copy = restore_database(args.backup_file, config.db_path)
            print(f"복원 완료: {config.db_path}")
            if safety_copy:
                print(f"이전 DB 사본: {safety_copy}")
    except BackupError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
