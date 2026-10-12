"""브라우저 테스트: 테마, 좁은 창, 키보드, 요청 수, 큰 목록 (US-14와 성능 기준)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from conftest import TEST_API_KEY

pytestmark = pytest.mark.e2e

LIGHT_BACKGROUND = "rgb(255, 255, 255)"
DARK_BACKGROUND = "rgb(32, 32, 32)"


def body_colors(page) -> tuple[str, str]:
    return tuple(
        page.evaluate(
            "() => { const s = getComputedStyle(document.body); return [s.backgroundColor, s.color]; }"
        )
    )


def has_horizontal_scroll(page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )


# --- US-14 테마 ---


def test_light_setting_gives_light_theme(ui):
    ui.page.emulate_media(color_scheme="light")
    ui.login()
    assert body_colors(ui.page) == (LIGHT_BACKGROUND, "rgb(27, 27, 27)")


def test_dark_setting_gives_dark_theme_including_dialog_and_inputs(ui):
    ui.page.emulate_media(color_scheme="dark")
    ui.server.seed("우유 사기")
    ui.login()
    assert body_colors(ui.page) == (DARK_BACKGROUND, "rgb(242, 242, 242)")

    input_background = ui.tid("add-form-input").evaluate(
        "node => getComputedStyle(node).backgroundColor"
    )
    assert input_background == DARK_BACKGROUND

    ui.tid("todo-item-delete-button").click()
    dialog_background = ui.tid("confirm-dialog").evaluate(
        "node => getComputedStyle(node).backgroundColor"
    )
    assert dialog_background == DARK_BACKGROUND


def test_theme_follows_the_setting_without_reload(ui):
    ui.page.emulate_media(color_scheme="light")
    ui.login()
    assert body_colors(ui.page)[0] == LIGHT_BACKGROUND
    ui.page.emulate_media(color_scheme="dark")
    assert body_colors(ui.page)[0] == DARK_BACKGROUND


# --- US-14 좁은 창 ---


def test_narrow_window_has_no_horizontal_scroll_even_with_long_titles(ui):
    ui.page.set_viewport_size({"width": 480, "height": 800})
    ui.server.seed("가" * 200, "W" * 200, "띄어 쓴 긴 제목 " * 20)
    ui.open()
    assert has_horizontal_scroll(ui.page) is False  # 키 입력 화면

    ui.tid("key-form-input").fill(TEST_API_KEY)
    ui.tid("key-form-submit-button").click()
    expect(ui.tid("todo-item")).to_have_count(3)
    assert has_horizontal_scroll(ui.page) is False

    # 모든 조작 요소가 창 안에 있다.
    for name in ["add-form-submit-button", "filter-completed-button", "refresh-button", "clear-key-button"]:
        box = ui.tid(name).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 480, name
    for button in ui.tid("todo-item-delete-button").all():
        box = button.bounding_box()
        assert box["x"] + box["width"] <= 480

    ui.tid("todo-item-delete-button").first.click()
    box = ui.tid("confirm-dialog").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 480


def test_wide_window_keeps_the_content_column_readable(ui):
    ui.page.set_viewport_size({"width": 1920, "height": 1080})
    ui.login()
    box = ui.page.locator("main").bounding_box()
    assert box["width"] <= 700
    assert abs((box["x"] + box["width"] / 2) - 960) < 2  # 가운데 정렬


# --- US-14 키보드 ---


def test_everything_can_be_done_with_the_keyboard_alone(ui):
    ui.server.seed("기존 항목")
    ui.open()
    keyboard = ui.page.keyboard

    # 키 입력: 포커스가 이미 입력 칸에 있다.
    keyboard.insert_text(TEST_API_KEY)
    keyboard.press("Enter")
    expect(ui.tid("list-view")).to_be_visible()

    # 추가: 포커스가 제목 입력 칸에 있다.
    expect(ui.tid("add-form-input")).to_be_focused()
    keyboard.insert_text("키보드로 추가")
    keyboard.press("Enter")
    expect(ui.tid("todo-item")).to_have_count(2)

    # Tab 순서: 입력 칸, 추가, 필터 셋, 새로고침, 키 지우기, 첫 항목의 체크 상자, 삭제
    order = [
        "add-form-submit-button",
        "filter-all-button",
        "filter-pending-button",
        "filter-completed-button",
        "refresh-button",
        "clear-key-button",
    ]
    for name in order:
        keyboard.press("Tab")
        expect(ui.tid(name)).to_be_focused()
    keyboard.press("Tab")
    first_checkbox = ui.item("키보드로 추가").get_by_test_id("todo-item-checkbox")
    expect(first_checkbox).to_be_focused()

    # 체크: Space
    keyboard.press("Space")
    expect(first_checkbox).to_be_checked()
    expect(first_checkbox).to_be_focused()
    # 저장 요청이 끝날 때까지는 같은 항목을 다시 조작할 수 없다.
    expect(ui.item("키보드로 추가")).to_have_attribute("aria-busy", "false")

    # 삭제: Tab으로 삭제 버튼, Enter로 확인 창, Tab으로 "삭제", Enter
    keyboard.press("Tab")
    keyboard.press("Enter")
    expect(ui.tid("confirm-dialog-cancel-button")).to_be_focused()
    keyboard.press("Tab")
    expect(ui.tid("confirm-dialog-confirm-button")).to_be_focused()
    keyboard.press("Enter")
    expect(ui.tid("todo-item")).to_have_count(1)
    assert ui.titles() == ["기존 항목"]
    # 지운 항목에 있던 포커스는 남은 항목으로 간다.
    expect(ui.item("기존 항목").get_by_test_id("todo-item-checkbox")).to_be_focused()

    # 필터: Shift+Tab으로 돌아가 Enter
    for _ in range(4):
        keyboard.press("Shift+Tab")
    expect(ui.tid("filter-pending-button")).to_be_focused()
    keyboard.press("Enter")
    expect(ui.tid("filter-pending-button")).to_have_attribute("aria-pressed", "true")
    expect(ui.tid("filter-pending-button")).to_be_focused()


def test_focus_stays_inside_the_dialog_while_it_is_open(ui):
    ui.server.seed("우유 사기")
    ui.login()
    ui.tid("todo-item-delete-button").focus()
    ui.page.keyboard.press("Enter")

    seen = set()
    for _ in range(6):
        ui.page.keyboard.press("Tab")
        seen.add(ui.page.evaluate("() => document.activeElement.dataset.testid ?? ''"))
    assert seen <= {"confirm-dialog-cancel-button", "confirm-dialog-confirm-button", ""}
    assert "add-form-input" not in seen


def test_keyboard_focus_is_visible(ui):
    ui.login()
    ui.page.keyboard.press("Tab")
    outline = ui.tid("add-form-submit-button").evaluate(
        "node => { const s = getComputedStyle(node); return [s.outlineStyle, s.outlineWidth]; }"
    )
    assert outline == ["solid", "2px"]


def test_controls_have_names_for_screen_readers(ui):
    ui.server.seed("우유 사기")
    ui.login()
    page = ui.page
    assert page.locator("html").get_attribute("lang") == "ko"
    expect(page.get_by_label("새 할 일")).to_have_count(1)
    expect(page.get_by_role("checkbox", name="우유 사기")).to_have_count(1)
    expect(page.get_by_role("button", name="삭제: 우유 사기")).to_have_count(1)
    expect(page.get_by_role("group", name="필터")).to_have_count(1)

    ui.add("   ")
    expect(ui.tid("notice")).to_have_attribute("role", "alert")
    ui.tid("todo-item-delete-button").click()
    expect(page.get_by_role("dialog", name="할 일 삭제")).to_be_visible()


# --- 요청 수 ---


def test_first_screen_takes_four_requests_and_no_icon_request(ui):
    ui.login()
    ui.requests.clear()
    ui.page.reload()
    expect(ui.tid("list-view")).to_be_visible()

    paths = sorted(url.removeprefix(ui.server.url) for url in ui.requests)
    assert paths == ["/api_test", "/api_test/app.css", "/api_test/app.js", "/todos"]


def test_idle_screen_sends_no_requests(ui):
    ui.page.clock.install()
    ui.login()
    ui.requests.clear()
    ui.page.clock.fast_forward("10:00")
    ui.page.wait_for_timeout(300)
    assert ui.requests == []


def test_each_action_takes_one_api_call(ui):
    ui.server.seed("우유 사기")
    ui.login()

    def calls_during(action) -> int:
        before = len(ui.api_requests())
        action()
        ui.page.wait_for_load_state("networkidle")
        return len(ui.api_requests()) - before

    assert calls_during(lambda: ui.add("새 항목")) == 1
    assert calls_during(lambda: ui.item("새 항목").get_by_test_id("todo-item-checkbox").click()) == 1
    assert calls_during(lambda: ui.tid("filter-pending-button").click()) == 1
    assert calls_during(lambda: ui.tid("refresh-button").click()) == 1

    def delete() -> None:
        ui.tid("todo-item-delete-button").first.click()
        ui.tid("confirm-dialog-confirm-button").click()

    assert calls_during(delete) == 1
    assert calls_during(lambda: ui.tid("clear-key-button").click()) == 0


# --- 큰 목록 ---


def test_thousand_items_are_listed_and_the_screen_stays_usable(ui):
    ui.server.seed_many(1000)
    ui.login()
    expect(ui.tid("todo-item")).to_have_count(1000)
    expect(ui.tid("todo-item-title").first).to_have_text("할 일 0999")

    ui.add("천 건 위에 추가")
    expect(ui.tid("todo-item")).to_have_count(1001)
    expect(ui.tid("todo-item-title").first).to_have_text("천 건 위에 추가")

    ui.tid("todo-item-checkbox").first.click()
    expect(ui.tid("todo-item").first).to_have_attribute("data-completed", "true")

    ui.tid("filter-completed-button").click()
    expect(ui.tid("todo-item")).to_have_count(1)
    ui.tid("filter-pending-button").click()
    expect(ui.tid("todo-item")).to_have_count(1000)
