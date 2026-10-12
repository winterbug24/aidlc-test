"""백업/복원 테스트 (RT-05~07)."""

from __future__ import annotations

import os
import stat

import pytest

from conftest import AUTH
from todo_api.app import create_app
from todo_api.backup import (
    BackupError,
    backup_database,
    list_backups,
    main,
    restore_database,
    verify_database,
)

posix_only = pytest.mark.skipif(os.name == "nt", reason="POSIX 파일 권한 검사")


def titles(client) -> list[str]:
    return [t["title"] for t in client.get("/todos", headers=AUTH).get_json()["todos"]]


def test_backup_creates_verified_copy_while_app_is_running(client, create, config):
    create("a")
    path = backup_database(config.db_path, config.backup_dir)
    assert path.parent == config.backup_dir
    assert verify_database(path)
    assert list_backups(config.backup_dir) == [path]


def test_rt05_restore_brings_data_back_to_backup_point(client, create, config):
    kept = create("백업 시점의 항목")
    backup = backup_database(config.db_path, config.backup_dir)
    create("백업 이후 항목")
    client.delete(f"/todos/{kept['id']}", headers=AUTH)
    assert titles(client) == ["백업 이후 항목"]

    safety_copy = restore_database(backup, config.db_path)

    restarted = create_app(config).test_client()
    assert titles(restarted) == ["백업 시점의 항목"]
    assert restarted.get("/health").status_code == 200
    # 복원 전 상태도 안전 사본으로 남는다.
    assert safety_copy is not None and verify_database(safety_copy)


def test_rt06_corrupt_backup_is_refused_and_database_is_untouched(
    client, create, config, tmp_path
):
    create("a")
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"garbage" * 500)
    empty = tmp_path / "empty.db"
    empty.touch()

    for candidate in (bad, empty, tmp_path / "missing.db"):
        assert not verify_database(candidate)
        with pytest.raises(BackupError):
            restore_database(candidate, config.db_path)

    assert titles(client) == ["a"]
    assert list(config.db_path.parent.glob("*before-restore*")) == []


def test_rt07_only_the_most_recent_backups_are_kept(client, config):
    created = [backup_database(config.db_path, config.backup_dir, keep=7) for _ in range(9)]
    assert list_backups(config.backup_dir) == created[-7:]


def test_backup_fails_clearly_when_database_is_missing(tmp_path):
    with pytest.raises(BackupError):
        backup_database(tmp_path / "none.db", tmp_path / "backups")
    assert list_backups(tmp_path / "backups") == []


@posix_only
def test_database_and_backup_files_are_owner_only(client, config):
    backup = backup_database(config.db_path, config.backup_dir)
    for path in (config.db_path, backup):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    for directory in (config.db_path.parent, config.backup_dir):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_command_line_backup_list_and_restore(client, create, config, monkeypatch, capsys):
    monkeypatch.setenv("TODO_DB_PATH", str(config.db_path))
    monkeypatch.setenv("TODO_BACKUP_DIR", str(config.backup_dir))
    monkeypatch.delenv("TODO_API_KEY", raising=False)
    create("a")

    assert main(["backup"]) == 0
    backup = list_backups(config.backup_dir)[0]
    assert main(["list"]) == 0
    assert str(backup) in capsys.readouterr().out

    assert main(["restore", str(backup)]) == 0
    assert main(["restore", str(config.backup_dir / "missing.db")]) == 1
    assert "오류" in capsys.readouterr().err
