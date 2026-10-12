"""실행 로직의 속성 기반 테스트 (Hypothesis).

속성 번호(WP-01~05)는 web-ui 기능 설계 business-logic-model.md 5장을 따른다.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from strategies import api_keys, port_states, process_lists
from todo_api.config import MIN_API_KEY_LENGTH, Config
from todo_api.launcher import (
    PortState,
    choose_port,
    format_key_file,
    generate_key,
    parse_key_file,
    select_project_servers,
)


def ports_in(states, wanted: PortState) -> list[int]:
    return sorted(port for port, state in states.items() if state is wanted)


@given(port_states())
def test_wp01_running_server_is_always_reused_at_its_lowest_port(states):
    ours = ports_in(states, PortState.OURS)
    selection = choose_port(states)
    if ours:
        assert (selection.action, selection.port) == ("reuse", ours[0])
    else:
        assert selection.action != "reuse"


@given(port_states())
def test_wp02_new_server_starts_only_on_the_lowest_free_port(states):
    selection = choose_port(states)
    if selection.action == "start":
        assert ports_in(states, PortState.OURS) == []
        assert selection.port == ports_in(states, PortState.FREE)[0]


@given(port_states())
def test_wp03_result_is_never_a_busy_or_unknown_port(states):
    selection = choose_port(states)
    usable = ports_in(states, PortState.OURS) + ports_in(states, PortState.FREE)
    if selection.action == "none":
        assert usable == []
        assert selection.port is None
    else:
        assert selection.port in states
        assert states[selection.port] is not PortState.BUSY
        assert usable != []


@given(api_keys())
def test_wp04_key_survives_being_written_to_and_read_from_the_key_file(key):
    assert parse_key_file(format_key_file(key)) == key


@given(api_keys(), st.lists(st.sampled_from(["# 설명", "OTHER=1", "", "  "]), max_size=4))
def test_wp04_other_lines_in_the_key_file_do_not_change_the_key(key, other_lines):
    text = "\n".join([*other_lines, format_key_file(key).strip(), *other_lines])
    assert parse_key_file(text) == key


@given(st.integers(min_value=0, max_value=20))
def test_wp05_generated_key_is_always_accepted_by_the_server_config(_n):
    key = generate_key()
    assert len(key) >= MIN_API_KEY_LENGTH
    assert parse_key_file(format_key_file(key)) == key
    # 길이 검증을 통과하지 못하면 여기서 ConfigError가 난다.
    assert Config.from_env({"TODO_API_KEY": key}).api_key == key


# --- 종료 대상 선택 (3차 워크플로, SNFR-05) ---

PROJECT = Path("/home/someone/project")
UID = 1000


@given(process_lists(str(PROJECT), UID))
def test_stop_selects_exactly_this_users_servers_in_this_project(processes):
    selected = select_project_servers(processes, PROJECT, UID)
    by_pid = {info.pid: info for info in processes}

    # 선택된 것은 모두 조건에 맞는다: 내 프로세스, 프로젝트 폴더, 서버 모듈 실행.
    for pid in selected:
        info = by_pid[pid]
        assert info.uid == UID
        assert info.cwd == str(PROJECT)
        assert info.argv[1:3] == ("-m", "todo_api.server")
    # 조건에 맞는 것은 빠짐없이 선택된다.
    expected = sorted(
        info.pid
        for info in processes
        if info.uid == UID
        and info.cwd == str(PROJECT)
        and info.argv[1:3] == ("-m", "todo_api.server")
    )
    assert selected == expected


@given(process_lists(str(PROJECT), UID))
def test_stop_never_selects_other_users_or_other_folders(processes):
    selected = set(select_project_servers(processes, PROJECT, UID))
    for info in processes:
        if info.uid != UID or info.cwd != str(PROJECT):
            assert info.pid not in selected
