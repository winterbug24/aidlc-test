"""실행 로직 테스트 (예제 기반): 키 파일, 포트 판정, 시작 흐름."""

from __future__ import annotations

import os
import socket
import stat
import threading
from contextlib import contextmanager

import pytest
from werkzeug.serving import make_server

from conftest import TEST_API_KEY, make_config
from todo_api import launcher
from todo_api.app import create_app
from todo_api.launcher import (
    Effects,
    LauncherError,
    PortState,
    Selection,
    choose_port,
    create_key_file,
    parse_windows_listening_ports,
    probe_ports,
    read_key,
    run_copy_key,
    run_start,
    wait_until_ready,
)

posix_only = pytest.mark.skipif(os.name == "nt", reason="POSIX 파일 권한 검사")

NETSTAT_SAMPLE = """
활성 연결

  프로토콜  로컬 주소              외부 주소              상태
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING
  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING
  TCP    127.0.0.1:49152        127.0.0.1:8003         ESTABLISHED
  TCP    [::]:445               [::]:0                 LISTENING
  TCP    [::1]:8002             [::]:0                 LISTENING
  UDP    0.0.0.0:8005           *:*
"""


@contextmanager
def running_app(tmp_path, **overrides):
    """실제 To-Do 앱을 임의의 빈 포트에 띄운다."""
    app = create_app(make_config(tmp_path, **overrides))
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join()


@contextmanager
def other_program():
    """HTTP가 아닌 다른 프로그램이 포트를 쓰는 상황."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        yield listener.getsockname()[1]


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class FakeProcess:
    def __init__(self, exit_code=None):
        self.exit_code = exit_code
        self.waited = False

    def poll(self):
        return self.exit_code

    def wait(self):
        self.waited = True
        return 0


class Recorder:
    """부수 효과를 기록만 하는 가짜."""

    def __init__(self, states, *, ready=True, windows_ports=frozenset()):
        self.said: list[str] = []
        self.copied: list[str] = []
        self.opened: list[str] = []
        self.started: list[int] = []
        self.stopped = 0
        self.process = FakeProcess()
        self.effects = Effects(
            say=self.said.append,
            copy_to_clipboard=lambda text: self.copied.append(text) or True,
            open_browser=lambda url: self.opened.append(url) or True,
            windows_listening_ports=lambda: None if windows_ports is None else set(windows_ports),
            probe_ports=lambda key, ports: dict(states),
            start_server=self._start,
            stop_server=self._stop,
            wait_until_ready=lambda port, process: ready,
        )

    def _start(self, port, key):
        self.started.append(port)
        return self.process

    def _stop(self, process):
        self.stopped += 1

    @property
    def output(self) -> str:
        return "\n".join(self.said)


def all_ports(state: PortState) -> dict[int, PortState]:
    return {port: state for port in launcher.CANDIDATE_PORTS}


# --- 순수 계산 ---


def test_choose_port_examples():
    free, busy, ours = PortState.FREE, PortState.BUSY, PortState.OURS
    assert choose_port({8000: free, 8001: free}) == Selection("start", 8000)
    assert choose_port({8000: busy, 8001: free}) == Selection("start", 8001)
    assert choose_port({8000: free, 8001: ours}) == Selection("reuse", 8001)
    assert choose_port({8000: busy, 8001: busy}) == Selection("none")
    assert choose_port({}) == Selection("none")


def test_windows_listening_ports_are_parsed_from_netstat_output():
    assert parse_windows_listening_ports(NETSTAT_SAMPLE) == {135, 8000, 445, 8002}
    assert parse_windows_listening_ports("") == set()


def test_page_url_never_contains_a_key():
    assert launcher.page_url(8001) == "http://127.0.0.1:8001/api_test"


# --- 키 파일 ---


def test_missing_key_file_reads_as_none(tmp_path):
    assert read_key(tmp_path / ".env") is None


def test_created_key_file_can_be_read_back(tmp_path):
    path = tmp_path / ".env"
    key = create_key_file(path)
    assert read_key(path) == key
    assert len(key) >= 32


@posix_only
def test_created_key_file_is_owner_only(tmp_path):
    path = tmp_path / ".env"
    create_key_file(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_existing_key_file_is_never_overwritten(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# 내 설정\nTODO_API_KEY=" + "k" * 40 + "\nOTHER=1\n", encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_key_file(path)
    assert read_key(path) == "k" * 40
    assert path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("content", ["", "OTHER=1\n", "TODO_API_KEY=\n", "TODO_API_KEY=short\n"])
def test_invalid_key_file_is_reported_and_left_alone(tmp_path, content):
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LauncherError):
        read_key(path)
    assert path.read_text(encoding="utf-8") == content


def test_quoted_key_is_accepted(tmp_path):
    path = tmp_path / ".env"
    path.write_text('TODO_API_KEY="' + "q" * 40 + '"\n', encoding="utf-8")
    assert read_key(path) == "q" * 40


# --- 환경 확인 (실제 소켓과 실제 앱) ---


def test_our_server_is_recognised_only_with_the_right_key(tmp_path):
    with running_app(tmp_path) as port:
        assert launcher.is_our_server(port, TEST_API_KEY) is True
        assert launcher.is_our_server(port, "x" * 40) is False
        assert launcher.is_healthy(port) is True


def test_other_programs_and_closed_ports_are_not_our_server():
    with other_program() as port:
        assert launcher.is_our_server(port, TEST_API_KEY, timeout=0.3) is False
        assert launcher.is_listening_locally(port) is True
    closed = free_port()
    assert launcher.is_our_server(closed, TEST_API_KEY) is False
    assert launcher.is_listening_locally(closed) is False
    assert launcher.is_healthy(closed) is False


def test_probe_classifies_ours_busy_and_free(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "PROBE_TIMEOUT_SECONDS", 0.3)
    with running_app(tmp_path) as ours, other_program() as busy:
        free = free_port()
        windows_only = free_port()
        states = probe_ports(
            TEST_API_KEY, {windows_only}, ports=[ours, busy, free, windows_only]
        )
    assert states == {
        ours: PortState.OURS,
        busy: PortState.BUSY,
        free: PortState.FREE,
        # WSL 안에서는 비어 보여도 Windows 프로그램이 쓰고 있으면 쓸 수 없다.
        windows_only: PortState.BUSY,
    }


def test_wait_until_ready_succeeds_once_the_server_answers(tmp_path):
    with running_app(tmp_path) as port:
        assert wait_until_ready(port, FakeProcess(), timeout=2, interval=0.01) is True


def test_wait_until_ready_gives_up_after_the_timeout():
    ticks = iter(range(100))
    slept = []
    ready = wait_until_ready(
        free_port(),
        FakeProcess(),
        timeout=3,
        interval=1,
        sleep=slept.append,
        clock=lambda: next(ticks),
    )
    assert ready is False
    assert slept == [1, 1]


def test_wait_until_ready_stops_immediately_when_the_server_process_died():
    slept = []
    ready = wait_until_ready(free_port(), FakeProcess(exit_code=2), sleep=slept.append)
    assert ready is False
    assert slept == []


# --- 시작 흐름 (가짜 부수 효과) ---


def test_first_run_creates_key_copies_it_and_starts_on_default_port(tmp_path):
    recorder = Recorder(all_ports(PortState.FREE))
    assert run_start(tmp_path, recorder.effects) == 0

    key = read_key(tmp_path / ".env")
    assert recorder.copied == [key]
    assert recorder.started == [8000]
    assert recorder.opened == ["http://127.0.0.1:8000/api_test"]
    assert recorder.process.waited is True
    assert recorder.stopped >= 1
    assert "붙여넣으세요" in recorder.output
    assert "Ctrl+C" in recorder.output
    # 키 값은 어디에도 출력하지 않는다.
    assert key not in recorder.output
    assert key not in "".join(recorder.opened)


def test_existing_key_is_reused_and_clipboard_is_left_alone(tmp_path):
    (tmp_path / ".env").write_text("TODO_API_KEY=" + "k" * 40 + "\n", encoding="utf-8")
    recorder = Recorder(all_ports(PortState.FREE))
    assert run_start(tmp_path, recorder.effects) == 0
    assert recorder.copied == []
    assert recorder.started == [8000]


def test_running_server_is_reused_without_starting_another(tmp_path):
    states = {**all_ports(PortState.FREE), 8003: PortState.OURS}
    recorder = Recorder(states)
    assert run_start(tmp_path, recorder.effects) == 0
    assert recorder.started == []
    assert recorder.opened == ["http://127.0.0.1:8003/api_test"]
    assert "이미 실행 중" in recorder.output


def test_busy_default_port_falls_back_to_next_free_port_with_a_note(tmp_path):
    states = {**all_ports(PortState.FREE), 8000: PortState.BUSY, 8001: PortState.BUSY}
    recorder = Recorder(states)
    assert run_start(tmp_path, recorder.effects) == 0
    assert recorder.started == [8002]
    assert recorder.opened == ["http://127.0.0.1:8002/api_test"]
    assert "http://127.0.0.1:8002/api_test" in recorder.output
    assert "키를 다시 입력" in recorder.output
    assert "todo-copy-key.bat" in recorder.output


def test_no_free_port_starts_nothing(tmp_path):
    recorder = Recorder(all_ports(PortState.BUSY))
    assert run_start(tmp_path, recorder.effects) == 1
    assert recorder.started == []
    assert recorder.opened == []
    assert "모두 사용 중" in recorder.output


def test_server_that_never_answers_is_stopped_and_browser_stays_closed(tmp_path):
    recorder = Recorder(all_ports(PortState.FREE), ready=False)
    assert run_start(tmp_path, recorder.effects) == 1
    assert recorder.started == [8000]
    assert recorder.opened == []
    assert recorder.stopped >= 1
    assert "todo-api.log" in recorder.output


def test_ctrl_c_stops_the_server(tmp_path):
    recorder = Recorder(all_ports(PortState.FREE))

    def interrupted():
        raise KeyboardInterrupt

    recorder.process.wait = interrupted
    assert run_start(tmp_path, recorder.effects) == 0
    assert recorder.stopped >= 1
    assert "종료" in recorder.output


def test_unreadable_windows_side_is_reported_but_does_not_block(tmp_path):
    recorder = Recorder(all_ports(PortState.FREE), windows_ports=None)
    assert run_start(tmp_path, recorder.effects) == 0
    assert "Windows 쪽 포트" in recorder.output
    assert recorder.started == [8000]


def test_invalid_key_file_stops_before_anything_starts(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TODO_API_KEY=short\n", encoding="utf-8")
    recorder = Recorder(all_ports(PortState.FREE))
    monkeypatch.setattr(launcher, "PROJECT_ROOT", tmp_path)
    assert launcher.main(["start"], recorder.effects) == 1
    assert recorder.started == []
    assert "오류" in recorder.output


# --- 키 복사 ---


def test_copy_key_copies_without_printing_the_key(tmp_path):
    key = create_key_file(tmp_path / ".env")
    recorder = Recorder({})
    assert run_copy_key(tmp_path, recorder.effects) == 0
    assert recorder.copied == [key]
    assert key not in recorder.output


def test_copy_key_without_key_file_points_to_the_start_file(tmp_path):
    recorder = Recorder({})
    assert run_copy_key(tmp_path, recorder.effects) == 1
    assert recorder.copied == []
    assert "todo-start.bat" in recorder.output
    assert not (tmp_path / ".env").exists()


def test_clipboard_failure_tells_where_the_key_is(tmp_path):
    create_key_file(tmp_path / ".env")
    recorder = Recorder({})
    recorder.effects.copy_to_clipboard = lambda text: False
    assert run_copy_key(tmp_path, recorder.effects) == 0
    assert ".env" in recorder.output


# --- 실제 서버 프로세스 ---


@posix_only
def test_real_server_process_starts_with_key_from_environment_and_stops(tmp_path, monkeypatch):
    port = free_port()
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "todo.db"))
    monkeypatch.setenv("TODO_LOG_DIR", str(tmp_path / "logs"))
    process = launcher.start_server(port, TEST_API_KEY)
    try:
        # 키는 인자가 아니라 환경 변수로 전달된다.
        assert TEST_API_KEY not in " ".join(process.args)
        assert wait_until_ready(port, process, timeout=15, interval=0.1) is True
        assert launcher.is_our_server(port, TEST_API_KEY) is True
    finally:
        launcher.stop_server(process)
    assert process.poll() is not None
    assert launcher.is_listening_locally(port) is False
