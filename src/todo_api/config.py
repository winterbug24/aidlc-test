"""환경 변수 기반 설정과 파일 보호 도우미."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIN_API_KEY_LENGTH = 32


class ConfigError(RuntimeError):
    """설정이 잘못되어 애플리케이션을 시작할 수 없음."""


@dataclass(frozen=True)
class Config:
    # repr에서 제외해 설정 객체가 로그에 찍혀도 키가 노출되지 않게 한다.
    api_key: str = field(repr=False)
    db_path: Path
    log_dir: Path | None
    backup_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    # 아래 값은 환경 변수로 노출하지 않는다. 테스트에서만 인자로 조정한다.
    log_to_stdout: bool = True
    max_content_length: int = 16 * 1024
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60 per minute"
    rate_limit_auth_failure: str = "10 per minute"
    db_timeout_seconds: float = 5.0
    backup_keep: int = 7

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key:
            raise ConfigError("TODO_API_KEY 환경 변수가 설정되지 않았습니다.")
        if len(self.api_key) < MIN_API_KEY_LENGTH:
            raise ConfigError(
                f"TODO_API_KEY는 {MIN_API_KEY_LENGTH}자 이상이어야 합니다."
            )
        if not 1 <= self.port <= 65535:
            raise ConfigError("TODO_PORT는 1에서 65535 사이여야 합니다.")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Config:
        env = os.environ if environ is None else environ
        try:
            port = int(env.get("TODO_PORT", "8000"))
        except ValueError as exc:
            raise ConfigError("TODO_PORT는 정수여야 합니다.") from exc
        return cls(
            api_key=env.get("TODO_API_KEY", ""),
            db_path=_resolve(env.get("TODO_DB_PATH", "instance/todo.db")),
            log_dir=_resolve(env.get("TODO_LOG_DIR", "logs")),
            backup_dir=_resolve(env.get("TODO_BACKUP_DIR", "backups")),
            host=env.get("TODO_HOST", "127.0.0.1"),
            port=port,
        )


def _resolve(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_private_dir(path: Path) -> None:
    """디렉터리가 없으면 소유자 전용 권한으로 만든다."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)


def create_private_file(path: Path) -> None:
    """파일이 없으면 소유자 전용 권한으로 만든다. 있으면 그대로 둔다."""
    os.close(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600))
