"""브라우저 테스트: 입력 오류, 요청 제한, 서버 연결 실패 (US-16, 17, 18).

서버 실패 상황은 요청 가로채기로 만든다. 실제 서버는 망가뜨리지 않는다.
"""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

from conftest import TEST_API_KEY

pytestmark = pytest.mark.e2e

TODOS_URL = re.compile(r"/todos(\?|/|$)")
NETWORK_MESSAGE = (
    "서버에 연결할 수 없습니다. 서버가 실행 중인지 확인한 뒤 새로고침을 눌러 주세요."
)


def respond(status: int, message: str, **headers: str):
    body = json.dumps({"error": {"code": "test", "message": message}})

    def handler(route):
        route.fulfill(
            status=status, headers=headers, content_type="application/json", body=body
        )

    return handler


# --- US-16 입력 오류 ---


def test_duplicate_title_shows_server_message_and_keeps_the_input(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.add("우유 사기")

    expect(ui.tid("notice-message")).to_have_text("같은 제목의 할 일이 이미 있습니다.")
    expect(ui.tid("notice")).to_have_attribute("data-kind", "error")
    expect(ui.tid("add-form-input")).to_have_value("우유 사기")
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.server.titles() == ["우유 사기"]


def test_other_server_rejections_show_the_server_message(ui):
    ui.login()
    ui.page.route(TODOS_URL, respond(400, "요청 값이 올바르지 않습니다."))
    ui.add("아무 제목")

    expect(ui.tid("notice-message")).to_have_text("요청 값이 올바르지 않습니다.")
    expect(ui.tid("add-form-input")).to_have_value("아무 제목")


def test_error_notice_goes_away_after_the_next_success(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.add("우유 사기")
    expect(ui.tid("notice")).to_be_visible()

    ui.add("다른 일")
    expect(ui.tid("todo-item")).to_have_count(2)
    expect(ui.tid("notice")).to_be_hidden()


def test_notice_can_be_closed(ui):
    ui.login()
    ui.add("   ")
    expect(ui.tid("notice")).to_be_visible()
    ui.tid("notice-close-button").click()
    expect(ui.tid("notice")).to_be_hidden()


def test_server_message_with_markup_is_shown_as_text(ui):
    ui.login()
    ui.page.route(TODOS_URL, respond(400, "<b>굵게</b><img src=x onerror=alert(1)>"))
    ui.add("아무 제목")

    expect(ui.tid("notice-message")).to_have_text("<b>굵게</b><img src=x onerror=alert(1)>")
    expect(ui.tid("notice").locator("b, img")).to_have_count(0)


# --- US-17 요청 제한 ---


def test_rate_limit_is_explained_and_the_list_stays(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.page.route(
        TODOS_URL,
        respond(429, "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", **{"Retry-After": "42"}),
    )
    ui.tid("refresh-button").click()

    message = ui.tid("notice-message")
    expect(message).to_contain_text("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    expect(message).to_contain_text("약 42초 후")
    assert ui.titles() == ["우유 사기"]
    assert ui.stored_key() == TEST_API_KEY


# --- US-18 서버에 연결할 수 없을 때 ---


def test_lost_connection_is_explained_and_recovers_on_retry(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.page.route(TODOS_URL, lambda route: route.abort())
    ui.tid("refresh-button").click()

    expect(ui.tid("notice-message")).to_have_text(NETWORK_MESSAGE)
    expect(ui.tid("loading-indicator")).to_be_hidden()
    assert ui.titles() == ["우유 사기"]

    # 추가도 같은 안내를 하고 입력을 지우지 않는다.
    ui.add("새 항목")
    expect(ui.tid("notice-message")).to_have_text(NETWORK_MESSAGE)
    expect(ui.tid("add-form-input")).to_have_value("새 항목")

    ui.page.unroute(TODOS_URL)
    ui.tid("refresh-button").click()
    expect(ui.tid("notice")).to_be_hidden()
    assert ui.titles() == ["우유 사기"]


def test_request_without_answer_times_out_after_15_seconds(ui):
    ui.page.clock.install()
    ui.server.seed("우유 사기")
    ui.login()
    held = []
    ui.page.route(TODOS_URL, lambda route: held.append(route))
    ui.tid("refresh-button").click()
    expect(ui.tid("loading-indicator")).to_be_visible()

    ui.page.clock.fast_forward(14_000)
    expect(ui.tid("loading-indicator")).to_be_visible()
    expect(ui.tid("notice")).to_be_hidden()

    ui.page.clock.fast_forward(1_500)
    expect(ui.tid("notice-message")).to_have_text(NETWORK_MESSAGE)
    expect(ui.tid("loading-indicator")).to_be_hidden()
    assert ui.titles() == ["우유 사기"]


def test_unavailable_database_shows_server_message_and_allows_retry(ui):
    ui.server.seed("우유 사기")
    ui.login()
    unavailable = "일시적으로 요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요."
    ui.page.route(TODOS_URL, respond(503, unavailable, **{"Retry-After": "5"}))
    ui.tid("refresh-button").click()
    expect(ui.tid("notice-message")).to_have_text(unavailable)
    assert ui.titles() == ["우유 사기"]

    ui.page.unroute(TODOS_URL)
    ui.tid("refresh-button").click()
    expect(ui.tid("notice")).to_be_hidden()


def test_unreadable_response_is_reported_with_its_status(ui):
    ui.login()
    ui.page.route(
        TODOS_URL,
        lambda route: route.fulfill(status=502, content_type="text/html", body="<h1>Bad</h1>"),
    )
    ui.tid("refresh-button").click()
    expect(ui.tid("notice-message")).to_have_text(
        "서버에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    )

    ui.page.unroute(TODOS_URL)
    ui.page.route(
        TODOS_URL,
        lambda route: route.fulfill(status=200, content_type="text/plain", body="not json"),
    )
    ui.tid("refresh-button").click()
    expect(ui.tid("notice-message")).to_have_text("예상하지 못한 응답입니다 (상태 코드 200).")


def test_opening_the_page_while_the_server_is_down_still_shows_a_usable_screen(ui):
    ui.login()
    ui.page.route(TODOS_URL, lambda route: route.abort())
    ui.page.reload()

    expect(ui.tid("list-view")).to_be_visible()
    expect(ui.tid("notice-message")).to_have_text(NETWORK_MESSAGE)
    expect(ui.tid("refresh-button")).to_be_enabled()
    # 연결 실패는 키 문제가 아니므로 저장된 키를 지우지 않는다.
    assert ui.stored_key() == TEST_API_KEY

    ui.page.unroute(TODOS_URL)
    ui.tid("refresh-button").click()
    expect(ui.tid("notice")).to_be_hidden()


def test_failed_filter_change_keeps_list_and_filter_consistent(ui):
    done, _pending = ui.server.seed("끝낸 일", "남은 일")
    ui.server.complete(done)
    ui.login()
    ui.page.route(TODOS_URL, lambda route: route.abort())
    ui.tid("filter-completed-button").click()

    expect(ui.tid("notice-message")).to_have_text(NETWORK_MESSAGE)
    # 불러오지 못했으면 화면의 목록(전체)과 필터 표시가 어긋나지 않게 되돌린다.
    expect(ui.tid("filter-all-button")).to_have_attribute("aria-pressed", "true")
    assert ui.titles() == ["남은 일", "끝낸 일"]
