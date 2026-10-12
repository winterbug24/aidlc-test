"""브라우저 테스트: 목록, 추가, 완료 체크, 삭제, 필터, 새로고침 (US-08~13)."""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

TODOS_URL = re.compile(r"/todos(\?|/|$)")


def checkbox(item):
    return item.get_by_test_id("todo-item-checkbox")


# --- US-08 목록 보기 ---


def test_list_is_newest_first_and_completed_items_look_different(ui):
    first, second, third = ui.server.seed("첫째", "둘째", "셋째")
    ui.server.complete(second)
    ui.login()

    assert ui.titles() == ["셋째", "둘째", "첫째"]
    done = ui.item("둘째")
    expect(checkbox(done)).to_be_checked()
    expect(checkbox(ui.item("첫째"))).not_to_be_checked()
    expect(done).to_have_attribute("data-completed", "true")
    decoration = done.get_by_test_id("todo-item-title").evaluate(
        "node => getComputedStyle(node).textDecorationLine"
    )
    assert decoration == "line-through"
    expect(ui.tid("empty-state")).to_be_hidden()


def test_empty_list_shows_a_hint(ui):
    ui.login()
    expect(ui.tid("empty-state")).to_have_text("할 일이 없습니다. 위에서 추가해 보세요.")
    expect(ui.tid("todo-item")).to_have_count(0)


def test_titles_are_shown_as_text_never_as_markup(ui):
    risky = ["<b>굵게</b> a < b", "<img src=x onerror=alert(1)>", "<script>alert(1)</script>"]
    ui.server.seed(*risky)
    ui.login()

    assert ui.titles() == risky[::-1]
    list_region = ui.tid("todo-list")
    for tag in ["b", "img", "script"]:
        expect(list_region.locator(tag)).to_have_count(0)


def test_loading_indicator_is_shown_while_the_list_is_requested(ui):
    ui.login()
    held = []
    ui.page.route(TODOS_URL, lambda route: held.append(route))
    ui.tid("refresh-button").click()

    expect(ui.tid("loading-indicator")).to_be_visible()
    held[0].continue_()
    expect(ui.tid("loading-indicator")).to_be_hidden()


# --- US-09 추가 ---


def test_add_with_enter_puts_new_item_on_top_and_clears_the_input(ui):
    ui.server.seed("기존 항목")
    ui.login()
    ui.add("새 항목")

    expect(ui.tid("todo-item")).to_have_count(2)
    assert ui.titles() == ["새 항목", "기존 항목"]
    expect(checkbox(ui.item("새 항목"))).not_to_be_checked()
    expect(ui.tid("add-form-input")).to_have_value("")
    expect(ui.tid("add-form-input")).to_be_focused()
    assert ui.server.titles() == ["새 항목", "기존 항목"]


def test_add_with_button_and_surrounding_whitespace_is_trimmed(ui):
    ui.login()
    ui.tid("add-form-input").fill("   책 반납   ")
    ui.tid("add-form-submit-button").click()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["책 반납"]


def test_blank_title_is_not_sent(ui):
    ui.login()
    before = len(ui.api_requests())
    ui.add("    ")
    expect(ui.tid("notice-message")).to_have_text("제목을 입력해 주세요.")
    expect(ui.tid("todo-item")).to_have_count(0)
    assert len(ui.api_requests()) == before


def test_input_accepts_at_most_200_characters(ui):
    ui.login()
    ui.tid("add-form-input").focus()
    ui.page.keyboard.insert_text("가" * 250)
    assert len(ui.tid("add-form-input").input_value()) == 200


# --- US-10 완료 체크와 해제 ---


def test_checking_and_unchecking_is_saved(ui):
    ui.server.seed("우유 사기")
    ui.login()

    checkbox(ui.item("우유 사기")).check()
    expect(ui.item("우유 사기")).to_have_attribute("data-completed", "true")
    ui.page.reload()
    expect(checkbox(ui.item("우유 사기"))).to_be_checked()

    checkbox(ui.item("우유 사기")).uncheck()
    expect(ui.item("우유 사기")).to_have_attribute("data-completed", "false")
    ui.page.reload()
    expect(checkbox(ui.item("우유 사기"))).not_to_be_checked()


def test_clicking_the_title_also_toggles(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.item("우유 사기").get_by_test_id("todo-item-title").click()
    expect(checkbox(ui.item("우유 사기"))).to_be_checked()


def test_rejected_change_is_rolled_back_on_screen(ui):
    ui.server.seed("우유 사기")
    ui.login()
    body = {"error": {"code": "internal_error", "message": "요청을 처리하는 중 오류가 발생했습니다."}}
    ui.page.route(
        re.compile(r"/todos/\d+$"),
        lambda route: route.fulfill(
            status=500, content_type="application/json", body=json.dumps(body)
        ),
    )
    checkbox(ui.item("우유 사기")).click()

    expect(ui.tid("notice-message")).to_have_text("요청을 처리하는 중 오류가 발생했습니다.")
    expect(checkbox(ui.item("우유 사기"))).not_to_be_checked()
    expect(ui.item("우유 사기")).to_have_attribute("data-completed", "false")


def test_item_deleted_elsewhere_is_removed_with_a_note(ui):
    (todo,) = ui.server.seed("우유 사기")
    ui.login()
    ui.server.delete(todo)
    checkbox(ui.item("우유 사기")).click()

    expect(ui.tid("notice-message")).to_have_text("이미 삭제된 할 일입니다.")
    expect(ui.tid("notice")).to_have_attribute("data-kind", "info")
    expect(ui.tid("todo-item")).to_have_count(0)


# --- US-11 삭제 ---


def test_delete_asks_first_and_cancel_keeps_the_item(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.item("우유 사기").get_by_test_id("todo-item-delete-button").click()

    dialog = ui.tid("confirm-dialog")
    expect(dialog).to_be_visible()
    expect(ui.tid("confirm-dialog-title")).to_have_text("우유 사기")
    expect(dialog).to_contain_text("삭제하면 되돌릴 수 없습니다.")
    expect(ui.tid("confirm-dialog-cancel-button")).to_be_focused()
    assert ui.server.titles() == ["우유 사기"]

    ui.tid("confirm-dialog-cancel-button").click()
    expect(dialog).to_be_hidden()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.server.titles() == ["우유 사기"]


def test_escape_cancels_the_delete(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.item("우유 사기").get_by_test_id("todo-item-delete-button").click()
    ui.page.keyboard.press("Escape")

    expect(ui.tid("confirm-dialog")).to_be_hidden()
    expect(ui.tid("todo-item")).to_have_count(1)
    # 닫히면 포커스가 누른 버튼으로 돌아온다.
    expect(ui.item("우유 사기").get_by_test_id("todo-item-delete-button")).to_be_focused()


def test_confirmed_delete_removes_the_item_for_good(ui):
    ui.server.seed("남길 항목", "지울 항목")
    ui.login()
    ui.item("지울 항목").get_by_test_id("todo-item-delete-button").click()
    ui.tid("confirm-dialog-confirm-button").click()

    expect(ui.tid("confirm-dialog")).to_be_hidden()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["남길 항목"]
    ui.page.reload()
    assert ui.titles() == ["남길 항목"]
    assert ui.server.titles() == ["남길 항목"]


def test_delete_dialog_shows_risky_title_as_text(ui):
    ui.server.seed("<i>기울임</i>")
    ui.login()
    ui.tid("todo-item-delete-button").click()
    expect(ui.tid("confirm-dialog-title")).to_have_text("<i>기울임</i>")
    expect(ui.tid("confirm-dialog").locator("i")).to_have_count(0)


# --- US-12 필터 ---


def test_filters_show_matching_items_and_mark_the_selected_one(ui):
    done, pending = ui.server.seed("끝낸 일", "남은 일")
    ui.server.complete(done)
    ui.login()

    expect(ui.tid("filter-all-button")).to_have_attribute("aria-pressed", "true")
    assert ui.titles() == ["남은 일", "끝낸 일"]

    ui.tid("filter-pending-button").click()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["남은 일"]
    expect(ui.tid("filter-pending-button")).to_have_attribute("aria-pressed", "true")
    expect(ui.tid("filter-all-button")).to_have_attribute("aria-pressed", "false")

    ui.tid("filter-completed-button").click()
    expect(ui.item("끝낸 일")).to_be_visible()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["끝낸 일"]

    ui.tid("filter-all-button").click()
    expect(ui.tid("todo-item")).to_have_count(2)


def test_item_leaves_a_filtered_list_when_it_no_longer_matches(ui):
    ui.server.seed("남은 일 1", "남은 일 2")
    ui.login()
    ui.tid("filter-pending-button").click()
    expect(ui.tid("todo-item")).to_have_count(2)

    checkbox(ui.item("남은 일 1")).click()
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["남은 일 2"]

    ui.tid("filter-completed-button").click()
    expect(ui.item("남은 일 1")).to_be_visible()


def test_filter_with_no_matches_shows_its_own_hint(ui):
    ui.server.seed("남은 일")
    ui.login()
    ui.tid("filter-completed-button").click()
    expect(ui.tid("empty-state")).to_have_text("해당하는 할 일이 없습니다.")


def test_adding_under_completed_filter_explains_why_it_is_not_listed(ui):
    ui.login()
    ui.tid("filter-completed-button").click()
    expect(ui.tid("empty-state")).to_be_visible()
    ui.add("새 항목")

    expect(ui.tid("notice-message")).to_have_text("추가했습니다. 현재 필터에서는 보이지 않습니다.")
    expect(ui.tid("notice")).to_have_attribute("data-kind", "info")
    expect(ui.tid("todo-item")).to_have_count(0)
    assert ui.server.titles() == ["새 항목"]


def test_filter_starts_at_all_on_every_visit(ui):
    ui.login()
    ui.tid("filter-completed-button").click()
    expect(ui.tid("filter-completed-button")).to_have_attribute("aria-pressed", "true")
    ui.page.reload()
    expect(ui.tid("filter-all-button")).to_have_attribute("aria-pressed", "true")


# --- US-13 새로고침 ---


def test_refresh_picks_up_outside_changes_and_keeps_the_filter(ui):
    ui.server.seed("처음 있던 일")
    ui.login()
    ui.tid("filter-pending-button").click()
    expect(ui.tid("todo-item")).to_have_count(1)

    ui.server.seed("밖에서 추가한 일")
    assert ui.titles() == ["처음 있던 일"]
    ui.tid("refresh-button").click()

    expect(ui.tid("todo-item")).to_have_count(2)
    assert ui.titles() == ["밖에서 추가한 일", "처음 있던 일"]
    expect(ui.tid("filter-pending-button")).to_have_attribute("aria-pressed", "true")
