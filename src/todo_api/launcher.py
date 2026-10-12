"""Windows 실행 파일이 호출하는 실행 로직: python -m todo_api.launcher {start,copy-key,stop}

세 층으로 나눈다.
- 순수 계산: 포트 선택, 키 파일 형식, 키 생성
- 환경 확인: 포트 상태 판정, 서버 응답 대기
- 부수 효과: 서버 프로세스, 클립보드, 브라우저 (Effects로 바꿔 끼울 수 있다)

API 키는 창에 출력하지 않고 어떤 프로세스의 명령줄 인자로도 넘기지 않는다.
"""

from __future__ import annotations

import argparse
import ctypes
import http.client
import enum
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from todo_api.config import MIN_API_KEY_LENGTH, PROJECT_ROOT

HOST = "127.0.0.1"
CANDIDATE_PORTS: tuple[int, ...] = tuple(range(8000, 8010))
DEFAULT_PORT = CANDIDATE_PORTS[0]
WEB_PATH = "/api_test"
KEY_FILE_NAME = ".env"
KEY_VARIABLE = "TODO_API_KEY"
SERVER_MODULE = "todo_api.server"

PROBE_TIMEOUT_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 20.0
READY_INTERVAL_SECONDS = 0.5
STOP_TIMEOUT_SECONDS = 5.0

# 경로 검색 순서에 따라 다른 프로그램이 실행되지 않게 절대 경로로 부른다.
WINDOWS_DIR = Path("/mnt/c/Windows")
WINDOWS_SYSTEM32 = WINDOWS_DIR / "System32"
CLIP_EXE = WINDOWS_SYSTEM32 / "clip.exe"
CMD_EXE = WINDOWS_SYSTEM32 / "cmd.exe"
NETSTAT_EXE = WINDOWS_SYSTEM32 / "netstat.exe"


class LauncherError(RuntimeError):
    """사용자에게 그대로 보여 줄 수 있는 실행 오류."""


# --- 순수 계산 ---


class PortState(enum.Enum):
    OURS = "ours"  # 이 To-Do 서버가 응답한다
    BUSY = "busy"  # 다른 프로그램이 쓰고 있다
    FREE = "free"  # 비어 있다


@dataclass(frozen=True)
class Selection:
    action: str  # "reuse", "start", "none"
    port: int | None = None


def choose_port(states: Mapping[int, PortState]) -> Selection:
    """이미 실행 중인 서버가 있으면 그것을 쓰고, 없으면 가장 낮은 빈 포트에서 시작한다."""
    ports = sorted(states)
    for port in ports:
        if states[port] is PortState.OURS:
            return Selection("reuse", port)
    for port in ports:
        if states[port] is PortState.FREE:
            return Selection("start", port)
    return Selection("none")


def generate_key() -> str:
    return secrets.token_urlsafe(32)


def format_key_file(key: str) -> str:
    return f"{KEY_VARIABLE}={key}\n"


def parse_key_file(text: str) -> str | None:
    """키 파일에서 키를 읽는다. 다른 줄은 무시한다."""
    prefix = f"{KEY_VARIABLE}="
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value or None
    return None


def parse_windows_listening_ports(netstat_output: str) -> set[int]:
    """`netstat -an -p TCP` 출력에서 수신 중인 포트 번호를 뽑는다."""
    ports: set[int] = set()
    for line in netstat_output.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0] != "TCP" or fields[-1] != "LISTENING":
            continue
        _, _, port = fields[1].rpartition(":")
        if port.isdigit():
            ports.add(int(port))
    return ports


def page_url(port: int) -> str:
    return f"http://{HOST}:{port}{WEB_PATH}"


# --- 환경 확인 ---

# 프록시 환경 변수가 있어도 루프백 호출은 직접 보낸다.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get(port: int, path: str, headers: Mapping[str, str], timeout: float):
    request = urllib.request.Request(f"http://{HOST}:{port}{path}", headers=dict(headers))
    return _OPENER.open(request, timeout=timeout)


def is_our_server(port: int, key: str, timeout: float = PROBE_TIMEOUT_SECONDS) -> bool:
    """그 포트의 /todos가 우리 키를 받아들이면 이 To-Do 서버다.

    WSL 안에서만 호출한다. 이 서버는 항상 WSL에서 실행되므로 Windows 쪽 프로그램에는
    키가 든 요청을 보내지 않는다.
    """
    try:
        with _get(port, "/todos", {"X-API-Key": key}, timeout) as response:
            payload = json.load(response)
            return response.status == 200 and isinstance(payload.get("todos"), list)
    except (OSError, ValueError, AttributeError, http.client.HTTPException):
        return False


def is_listening_locally(port: int, timeout: float = PROBE_TIMEOUT_SECONDS) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_healthy(port: int, timeout: float = PROBE_TIMEOUT_SECONDS) -> bool:
    try:
        with _get(port, "/health", {}, timeout) as response:
            return response.status == 200
    except (OSError, ValueError, http.client.HTTPException):
        return False


def probe_ports(
    key: str,
    windows_ports: set[int] | None,
    ports: Iterable[int] = CANDIDATE_PORTS,
) -> dict[int, PortState]:
    """포트별 상태를 판정한다. Windows 쪽과 WSL 쪽 모두 비어 있어야 빈 포트다."""
    windows_ports = windows_ports or set()
    states: dict[int, PortState] = {}
    for port in ports:
        if is_our_server(port, key):
            states[port] = PortState.OURS
        elif port in windows_ports or is_listening_locally(port):
            states[port] = PortState.BUSY
        else:
            states[port] = PortState.FREE
    return states


def wait_until_ready(
    port: int,
    process: subprocess.Popen,
    *,
    timeout: float = READY_TIMEOUT_SECONDS,
    interval: float = READY_INTERVAL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """서버가 응답할 때까지 기다린다. 서버 프로세스가 먼저 끝나면 바로 포기한다."""
    deadline = clock() + timeout
    while True:
        if process.poll() is not None:
            return False
        if is_healthy(port):
            return True
        if clock() >= deadline:
            return False
        sleep(interval)


# --- 키 파일 ---


def read_key(key_path: Path) -> str | None:
    """키 파일의 키를 돌려준다. 파일이 없으면 None, 내용이 잘못됐으면 오류."""
    if not key_path.is_file():
        return None
    key = parse_key_file(key_path.read_text(encoding="utf-8"))
    if key is None or len(key) < MIN_API_KEY_LENGTH:
        raise LauncherError(
            f"{key_path} 에 {MIN_API_KEY_LENGTH}자 이상의 {KEY_VARIABLE} 값이 없습니다. "
            "파일을 고치거나 지운 뒤 다시 실행해 주세요."
        )
    return key


def create_key_file(key_path: Path) -> str:
    """새 키를 만들어 소유자 전용 권한의 새 파일에 쓴다. 이미 있는 파일은 건드리지 않는다."""
    key = generate_key()
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(format_key_file(key))
    return key


# --- 부수 효과 ---


def _run_windows(command: list[str], **kwargs) -> subprocess.CompletedProcess | None:
    try:
        # Windows 프로그램은 WSL 경로를 현재 디렉터리로 쓰지 못하므로 Windows 디렉터리에서 실행한다.
        return subprocess.run(command, cwd=WINDOWS_DIR, timeout=10, check=False, **kwargs)
    except (OSError, subprocess.SubprocessError):
        return None


def copy_to_clipboard(text: str) -> bool:
    # 키는 인자가 아니라 표준 입력으로 넘긴다.
    if not text.isascii():
        return False
    result = _run_windows(
        [str(CLIP_EXE)],
        input=text.encode("ascii"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result is not None and result.returncode == 0


def open_browser(url: str) -> bool:
    result = _run_windows(
        [str(CMD_EXE), "/c", "start", "", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result is not None and result.returncode == 0


def windows_listening_ports() -> set[int] | None:
    """Windows 쪽에서 수신 중인 포트. 확인할 수 없으면 None."""
    result = _run_windows([str(NETSTAT_EXE), "-an", "-p", "TCP"], capture_output=True)
    if result is None or result.returncode != 0:
        return None
    return parse_windows_listening_ports(result.stdout.decode("ascii", errors="replace"))


def _terminate_with_parent() -> None:
    # 실행 로직이 강제로 죽어도 서버가 남지 않게 한다 (Linux 전용).
    try:
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass


def start_server(port: int, key: str) -> subprocess.Popen:
    source_dir = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        KEY_VARIABLE: key,  # 인자가 아니라 환경 변수로 넘긴다.
        "TODO_HOST": HOST,
        "TODO_PORT": str(port),
        "PYTHONPATH": str(source_dir),
    }
    return subprocess.Popen(
        [sys.executable, "-m", SERVER_MODULE],
        cwd=PROJECT_ROOT,
        env=env,
        # 요청 로그가 창을 채우지 않게 한다. 로그는 로그 파일에 남는다.
        stdout=subprocess.DEVNULL,
        preexec_fn=_terminate_with_parent,
    )


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


# --- 실행 중인 서버 찾기와 종료 ---


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    uid: int
    argv: tuple[str, ...]
    cwd: str | None


def is_project_server(info: ProcessInfo, project_root: Path, uid: int) -> bool:
    """이 프로젝트 폴더에서 `python -m todo_api.server`로 실행된 내 프로세스인가.

    이름의 일부 일치가 아니라 실행 인자와 작업 폴더의 정확한 일치로 판정한다.
    다른 프로그램, 다른 폴더, 다른 사용자의 프로세스를 끄지 않기 위해서다.
    """
    if info.uid != uid or info.cwd is None or info.cwd != str(project_root):
        return False
    # argv[0]은 실행 파일이다. 그 뒤에 "-m", "todo_api.server"가 연속으로 있어야 한다.
    return any(
        info.argv[index] == "-m" and info.argv[index + 1] == SERVER_MODULE
        for index in range(1, len(info.argv) - 1)
    )


def select_project_servers(
    processes: Iterable[ProcessInfo], project_root: Path, uid: int
) -> list[int]:
    """종료 대상 프로세스 번호를 오름차순으로 돌려준다 (순수 계산)."""
    return sorted(
        info.pid for info in processes if is_project_server(info, project_root, uid)
    )


def list_processes(proc_dir: Path = Path("/proc")) -> list[ProcessInfo]:
    """실행 중인 프로세스 목록을 읽는다 (Linux/WSL). 읽는 사이 끝난 프로세스는 건너뛴다."""
    processes: list[ProcessInfo] = []
    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
            uid = entry.stat().st_uid
        except OSError:
            continue
        try:
            cwd: str | None = os.readlink(entry / "cwd")
        except OSError:
            cwd = None
        argv = tuple(part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part)
        processes.append(ProcessInfo(int(entry.name), uid, argv, cwd))
    return processes


def is_running(pid: int, proc_dir: Path = Path("/proc")) -> bool:
    """프로세스가 아직 돌고 있는가. 끝났지만 정리되지 않은 것(좀비)은 끝난 것으로 본다."""
    try:
        stat = (proc_dir / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # 형식: "pid (이름) 상태 ...". 이름에 괄호가 들어갈 수 있어 마지막 ')' 뒤를 본다.
    state = stat.rpartition(")")[2].split()[:1]
    return state != ["Z"]


def stop_processes(
    pids: Iterable[int],
    *,
    timeout: float = STOP_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    running: Callable[[int], bool] = is_running,
    send_signal: Callable[[int, int], None] = os.kill,
) -> tuple[list[int], list[int]]:
    """정상 종료를 요청하고, 기다려도 남아 있으면 강제로 끝낸다.

    (끝난 프로세스, 끝내지 못한 프로세스)를 돌려준다.
    """
    targets = list(pids)

    def signal_all(signum: int) -> None:
        for pid in targets:
            if running(pid):
                try:
                    send_signal(pid, signum)
                except OSError:
                    pass  # 그사이 끝났거나 권한이 없다. 아래에서 다시 확인한다.

    def wait_for_exit(limit: float) -> None:
        deadline = clock() + limit
        while any(running(pid) for pid in targets) and clock() < deadline:
            sleep(0.1)

    signal_all(signal.SIGTERM)
    wait_for_exit(timeout)
    if any(running(pid) for pid in targets):
        signal_all(signal.SIGKILL)
        wait_for_exit(1.0)

    remaining = [pid for pid in targets if running(pid)]
    stopped = [pid for pid in targets if pid not in remaining]
    return stopped, remaining


@dataclass
class Effects:
    """바깥 세계에 영향을 주는 동작. 테스트에서는 가짜로 바꿔 끼운다."""

    say: Callable[[str], None] = print
    copy_to_clipboard: Callable[[str], bool] = copy_to_clipboard
    open_browser: Callable[[str], bool] = open_browser
    windows_listening_ports: Callable[[], set[int] | None] = windows_listening_ports
    probe_ports: Callable[[str, set[int] | None], dict[int, PortState]] = probe_ports
    start_server: Callable[[int, str], subprocess.Popen] = start_server
    stop_server: Callable[[subprocess.Popen], None] = stop_server
    wait_until_ready: Callable[..., bool] = wait_until_ready
    list_processes: Callable[[], list[ProcessInfo]] = list_processes
    stop_processes: Callable[..., tuple[list[int], list[int]]] = stop_processes
    log_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")


# --- 명령 ---


def _offer_key(key: str, effects: Effects) -> None:
    if effects.copy_to_clipboard(key):
        effects.say("API 키를 클립보드에 복사했습니다. 화면의 키 입력 칸에 붙여넣으세요.")
    else:
        effects.say(
            "API 키를 클립보드에 복사하지 못했습니다. "
            f"{KEY_FILE_NAME} 파일의 {KEY_VARIABLE} 값을 직접 복사해 주세요."
        )


def _open_page(port: int, effects: Effects) -> None:
    url = page_url(port)
    if not effects.open_browser(url):
        effects.say(f"브라우저를 열지 못했습니다. 주소를 직접 열어 주세요: {url}")


def run_start(project_root: Path, effects: Effects) -> int:
    key_path = project_root / KEY_FILE_NAME
    key = read_key(key_path)
    if key is None:
        key = create_key_file(key_path)
        effects.say(f"새 API 키를 만들어 {KEY_FILE_NAME} 파일에 저장했습니다.")
        _offer_key(key, effects)

    windows_ports = effects.windows_listening_ports()
    if windows_ports is None:
        effects.say("Windows 쪽 포트 사용 여부를 확인하지 못했습니다. WSL 쪽만 확인하고 진행합니다.")
    selection = choose_port(effects.probe_ports(key, windows_ports))

    if selection.action == "reuse":
        effects.say(f"이미 실행 중인 서버를 사용합니다: {page_url(selection.port)}")
        _open_page(selection.port, effects)
        return 0
    if selection.action == "none":
        effects.say(
            f"{CANDIDATE_PORTS[0]}~{CANDIDATE_PORTS[-1]}번 포트가 모두 사용 중이라 "
            "서버를 시작하지 못했습니다."
        )
        return 1

    port = selection.port
    effects.say(f"서버를 시작합니다 (포트 {port})...")
    process = effects.start_server(port, key)
    try:
        if not effects.wait_until_ready(port, process):
            effects.stop_server(process)
            effects.say(
                "서버가 응답하지 않아 시작하지 못했습니다. "
                f"로그를 확인해 주세요: {effects.log_dir / 'todo-api.log'}"
            )
            return 1

        effects.say(f"화면 주소: {page_url(port)}")
        if port != DEFAULT_PORT:
            effects.say(
                f"{DEFAULT_PORT}번 포트가 사용 중이라 {port}번으로 시작했습니다. "
                "이 주소에서는 키를 다시 입력해야 할 수 있습니다. "
                "키가 필요하면 todo-copy-key.bat 을 실행하세요."
            )
        effects.say("이 창을 닫거나 Ctrl+C를 누르면 서버가 꺼집니다.")
        _open_page(port, effects)
        exit_code = process.wait()
        # todo-stop.bat 등으로 밖에서 서버를 끈 경우에도 여기로 온다.
        effects.say("서버가 종료되었습니다.")
        return exit_code
    except KeyboardInterrupt:
        effects.say("서버를 종료합니다.")
        return 0
    finally:
        effects.stop_server(process)


def run_copy_key(project_root: Path, effects: Effects) -> int:
    key = read_key(project_root / KEY_FILE_NAME)
    if key is None:
        effects.say("아직 API 키가 없습니다. todo-start.bat 을 먼저 실행해 주세요.")
        return 1
    _offer_key(key, effects)
    return 0


def run_stop(project_root: Path, effects: Effects) -> int:
    """이 프로젝트 폴더에서 실행 중인 To-Do 서버를 모두 끈다. API 키는 쓰지 않는다."""
    targets = select_project_servers(effects.list_processes(), project_root, os.getuid())
    if not targets:
        effects.say("실행 중인 서버가 없습니다.")
        return 0

    stopped, remaining = effects.stop_processes(targets)
    if stopped:
        effects.say(f"서버 {len(stopped)}개를 종료했습니다.")
    if remaining:
        numbers = ", ".join(str(pid) for pid in remaining)
        effects.say(
            f"서버 {len(remaining)}개를 종료하지 못했습니다 (프로세스 번호: {numbers}). "
            "WSL 터미널에서 직접 확인해 주세요."
        )
        return 1
    return 0


def _raise_interrupt(_signum, _frame) -> None:
    raise KeyboardInterrupt


def main(argv: list[str] | None = None, effects: Effects | None = None) -> int:
    parser = argparse.ArgumentParser(description="To-Do 서버 실행 도구")
    parser.add_argument("command", choices=["start", "copy-key", "stop"])
    args = parser.parse_args(argv)
    effects = effects or Effects()

    # 창이 닫히거나 종료 신호가 오면 Ctrl+C와 같은 경로로 서버를 정리한다.
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _raise_interrupt)

    try:
        if args.command == "start":
            return run_start(PROJECT_ROOT, effects)
        if args.command == "stop":
            return run_stop(PROJECT_ROOT, effects)
        return run_copy_key(PROJECT_ROOT, effects)
    except LauncherError as exc:
        effects.say(f"오류: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
