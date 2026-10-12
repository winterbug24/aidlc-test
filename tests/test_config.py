"""설정 단위 테스트 (예제 기반). RT-08: 키 없이는 시작을 거부한다."""

from __future__ import annotations

from pathlib import Path

import pytest

from todo_api import server
from todo_api.config import PROJECT_ROOT, Config, ConfigError

VALID_KEY = "k" * 32


def test_defaults_bind_to_loopback_and_use_project_paths():
    config = Config.from_env({"TODO_API_KEY": VALID_KEY})
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.db_path == PROJECT_ROOT / "instance" / "todo.db"
    assert config.log_dir == PROJECT_ROOT / "logs"
    assert config.backup_dir == PROJECT_ROOT / "backups"
    assert config.rate_limit_enabled is True


def test_environment_overrides_are_applied(tmp_path: Path):
    config = Config.from_env(
        {
            "TODO_API_KEY": VALID_KEY,
            "TODO_DB_PATH": str(tmp_path / "x.db"),
            "TODO_HOST": "0.0.0.0",
            "TODO_PORT": "9001",
        }
    )
    assert config.db_path == tmp_path / "x.db"
    assert (config.host, config.port) == ("0.0.0.0", 9001)


@pytest.mark.parametrize("key", ["", "short", "k" * 31])
def test_missing_or_short_api_key_is_rejected(key):
    with pytest.raises(ConfigError):
        Config.from_env({"TODO_API_KEY": key})


def test_absent_api_key_is_rejected():
    with pytest.raises(ConfigError):
        Config.from_env({})


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_invalid_port_is_rejected(port):
    with pytest.raises(ConfigError):
        Config.from_env({"TODO_API_KEY": VALID_KEY, "TODO_PORT": port})


def test_api_key_is_not_exposed_in_repr():
    assert VALID_KEY not in repr(Config.from_env({"TODO_API_KEY": VALID_KEY}))


def test_server_refuses_to_start_without_api_key(monkeypatch, capsys):
    monkeypatch.delenv("TODO_API_KEY", raising=False)
    started = []
    monkeypatch.setattr(server, "create_app", lambda config: started.append(config))
    monkeypatch.setattr(server, "serve", lambda *args, **kwargs: started.append("serve"))

    assert server.main() == 2
    assert started == []
    assert "TODO_API_KEY" in capsys.readouterr().err
