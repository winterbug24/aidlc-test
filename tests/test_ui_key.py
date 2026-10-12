"""브라우저 테스트: 키 입력, 저장, 지우기 (US-05, 06, 07, 15, 17)."""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

from conftest import TEST_API_KEY, Ui, make_config, running_server

pytestmark = pytest.mark.e2e

TODOS_URL = re.compile(r"/todos(\?|/|$)")


def test_key_view_is_shown_and_list_is_hidden_without_stored_key(ui):
    ui.server.seed("비공개 항목")
    ui.open()
    expect(ui.tid("key-view")).to_be_visible()
    expect(ui.tid("list-view")).to_be_hidden()
    expect(ui.tid("todo-item")).to_have_count(0)
    expect(ui.tid("key-form-input")).to_be_focused()
    # 키가 없으면 API를 호출하지 않는다.
    assert ui.api_requests() == []


def test_key_input_hides_what_is_typed_without_being_a_password_field(ui):
    ui.open()
    field = ui.tid("key-form-input")
    assert field.get_attribute("type") == "text"
    assert field.get_attribute("autocomplete") == "off"
    assert field.evaluate("node => getComputedStyle(node).webkitTextSecurity") == "disc"


def test_correct_key_opens_the_list_and_is_stored(ui):
    ui.server.seed("우유 사기")
    ui.open()
    ui.tid("key-form-input").fill(TEST_API_KEY)
    ui.tid("key-form-submit-button").click()

    expect(ui.tid("list-view")).to_be_visible()
    expect(ui.tid("key-view")).to_be_hidden()
    assert ui.titles() == ["우유 사기"]
    assert ui.stored_key() == TEST_API_KEY
    expect(ui.tid("notice")).to_be_hidden()
    # 키 검증에 쓴 목록 조회가 곧 첫 목록이다 (요청 1회).
    assert len(ui.api_requests()) == 1


def test_enter_submits_and_pasted_whitespace_is_ignored(ui):
    ui.open()
    ui.tid("key-form-input").fill(f"  {TEST_API_KEY} \t")
    ui.tid("key-form-input").press("Enter")
    expect(ui.tid("list-view")).to_be_visible()
    assert ui.stored_key() == TEST_API_KEY


def test_key_never_appears_in_address_or_page_text(ui):
    ui.login()
    assert TEST_API_KEY not in ui.page.url
    assert TEST_API_KEY not in ui.page.locator("body").inner_text()
    assert all(TEST_API_KEY not in url for url in ui.requests)
    assert ui.tid("key-form-input").input_value() == ""


def test_empty_key_is_not_sent(ui):
    ui.open()
    ui.tid("key-form-input").fill("   ")
    ui.tid("key-form-submit-button").click()
    expect(ui.tid("notice-message")).to_have_text("API 키를 입력해 주세요.")
    expect(ui.tid("key-view")).to_be_visible()
    assert ui.api_requests() == []


def test_wrong_key_is_reported_and_not_stored(ui):
    ui.open()
    ui.tid("key-form-input").fill("wrong-key")
    ui.tid("key-form-submit-button").click()

    expect(ui.tid("notice-message")).to_have_text("API 키가 올바르지 않습니다.")
    expect(ui.tid("notice")).to_have_attribute("data-kind", "error")
    expect(ui.tid("notice")).to_contain_text("오류")
    expect(ui.tid("key-view")).to_be_visible()
    expect(ui.tid("list-view")).to_be_hidden()
    assert ui.stored_key() is None

    # 고쳐서 다시 내면 들어가고 오류 안내가 사라진다.
    ui.tid("key-form-input").fill(TEST_API_KEY)
    ui.tid("key-form-submit-button").click()
    expect(ui.tid("list-view")).to_be_visible()
    expect(ui.tid("notice")).to_be_hidden()


def test_next_visit_goes_straight_to_the_list(ui):
    ui.server.seed("우유 사기")
    ui.login()

    ui.page.reload()
    expect(ui.tid("list-view")).to_be_visible()
    expect(ui.tid("key-view")).to_be_hidden()
    assert ui.titles() == ["우유 사기"]

    # 같은 브라우저의 새 탭에서도 바로 들어간다.
    other = ui.page.context.new_page()
    other.goto(ui.server.page_url)
    expect(other.get_by_test_id("list-view")).to_be_visible()
    other.close()


def test_clear_key_returns_to_key_view_and_forgets_everything(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.tid("clear-key-button").click()

    expect(ui.tid("key-view")).to_be_visible()
    expect(ui.tid("list-view")).to_be_hidden()
    expect(ui.tid("todo-item")).to_have_count(0)
    expect(ui.tid("key-form-input")).to_be_focused()
    assert ui.stored_key() is None

    ui.page.reload()
    expect(ui.tid("key-view")).to_be_visible()
    # 지우기는 화면에서만 일어난다. 서버의 데이터는 그대로다.
    assert ui.server.titles() == ["우유 사기"]


def test_changed_server_key_sends_user_back_to_key_view_on_load(ui):
    ui.login()
    ui.page.evaluate("() => window.localStorage.setItem('todoApiKey', 'no-longer-valid')")
    ui.page.reload()

    expect(ui.tid("key-view")).to_be_visible()
    expect(ui.tid("notice-message")).to_have_text(
        "API 키가 올바르지 않거나 바뀌었습니다. 다시 입력해 주세요."
    )
    assert ui.stored_key() is None


def test_changed_server_key_is_detected_during_an_action(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.page.evaluate("() => window.localStorage.setItem('todoApiKey', 'no-longer-valid')")
    ui.tid("refresh-button").click()

    expect(ui.tid("key-view")).to_be_visible()
    expect(ui.tid("notice-message")).to_contain_text("다시 입력해 주세요")
    expect(ui.tid("todo-item")).to_have_count(0)
    assert ui.stored_key() is None


def test_auth_failure_limit_is_explained_differently_from_a_wrong_key(ui):
    body = {"error": {"code": "rate_limited", "message": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."}}
    ui.page.route(
        TODOS_URL,
        lambda route: route.fulfill(
            status=429,
            headers={"Retry-After": "30"},
            content_type="application/json",
            body=json.dumps(body),
        ),
    )
    ui.open()
    ui.tid("key-form-input").fill(TEST_API_KEY)
    ui.tid("key-form-submit-button").click()

    message = ui.tid("notice-message")
    expect(message).to_contain_text("요청이 너무 많습니다")
    expect(message).to_contain_text("약 30초 후")
    expect(message).not_to_contain_text("올바르지 않습니다")
    expect(ui.tid("key-view")).to_be_visible()
    assert ui.stored_key() is None


def test_real_auth_failure_limit_blocks_even_the_right_key_and_says_so(page, tmp_path):
    """실제 서버의 인증 실패 한도에 걸린 경우 (한도를 3회로 낮춘 설정)."""
    config = make_config(
        tmp_path,
        rate_limit_enabled=True,
        rate_limit_default="1000 per hour",
        rate_limit_auth_failure="3 per hour",
    )
    with running_server(config) as server:
        ui = Ui(page, server)
        ui.open()
        for _ in range(3):
            ui.tid("key-form-input").fill("wrong-key")
            ui.tid("key-form-submit-button").click()
            expect(ui.tid("notice-message")).to_have_text("API 키가 올바르지 않습니다.")
            expect(ui.tid("key-form-submit-button")).to_be_enabled()

        # 한도를 넘은 뒤에는 올바른 키도 거부된다. 안내는 틀린 키와 구분된다.
        ui.tid("key-form-input").fill(TEST_API_KEY)
        ui.tid("key-form-submit-button").click()
        message = ui.tid("notice-message")
        expect(message).to_contain_text("요청이 너무 많습니다")
        expect(message).to_contain_text("약 3600초 후")
        expect(message).not_to_contain_text("올바르지 않습니다")
        expect(ui.tid("key-view")).to_be_visible()
        assert ui.stored_key() is None
        assert ui.problems == []
