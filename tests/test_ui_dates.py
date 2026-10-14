"""브라우저 테스트: 목록의 등록 일자와 완료 일자 표시 (4차 워크플로 DFR-04, 05)."""

from __future__ import annotations

import sqlite3

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e, pytest.mark.browser_context_args(timezone_id="Asia/Seoul")]


def set_times(ui, todo: dict, *, created_at: str, completed: bool, completed_at: str | None):
    """화면이 읽을 시각을 DB에 직접 넣는다 (API는 시각을 받지 않는다)."""
    conn = sqlite3.connect(ui.server.config.db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE todos SET created_at = ?, completed = ?, completed_at = ? WHERE id = ?",
                (created_at, int(completed), completed_at, todo["id"]),
            )
    finally:
        conn.close()


def created(item):
    return item.get_by_test_id("todo-item-created-date")


def completed(item):
    return item.get_by_test_id("todo-item-completed-date")


def today(ui) -> str:
    return ui.page.evaluate(
        """() => {
          const d = new Date();
          return [d.getFullYear(), d.getMonth() + 1, d.getDate()]
            .map((n, i) => String(n).padStart(i ? 2 : 4, "0")).join("/");
        }"""
    )


def test_dates_follow_the_browser_time_zone(ui):
    (todo,) = ui.server.seed("장보기")
    # UTC 15:30은 한국 시간으로 다음 날 00:30이다.
    set_times(
        ui,
        todo,
        created_at="2026-10-13T15:30:00.000000Z",
        completed=True,
        completed_at="2026-10-15T14:59:59.999999Z",
    )
    ui.login()

    item = ui.item("장보기")
    expect(created(item)).to_have_text("등록 2026/10/14")
    expect(completed(item)).to_have_text("완료 2026/10/15")
    expect(completed(item)).to_be_visible()
    expect(item.locator("time.todo-created")).to_have_attribute("datetime", "2026-10-14")


@pytest.mark.browser_context_args(timezone_id="UTC")
def test_dates_in_utc_time_zone(ui):
    (todo,) = ui.server.seed("장보기")
    set_times(
        ui,
        todo,
        created_at="2026-10-13T15:30:00.000000Z",
        completed=True,
        completed_at="2026-10-15T14:59:59.999999Z",
    )
    ui.login()
    item = ui.item("장보기")
    expect(created(item)).to_have_text("등록 2026/10/13")
    expect(completed(item)).to_have_text("완료 2026/10/15")


def test_pending_item_shows_only_the_registration_date(ui):
    ui.server.seed("미완료 항목")
    ui.login()

    item = ui.item("미완료 항목")
    expect(created(item)).to_have_text(f"등록 {today(ui)}")
    expect(created(item)).to_be_visible()
    expect(completed(item)).not_to_be_visible()
    expect(completed(item).locator("time")).to_have_text("")


def test_item_completed_before_the_update_shows_a_dash(ui):
    (todo,) = ui.server.seed("예전 항목")
    set_times(
        ui, todo, created_at="2026-10-12T05:00:00.000000Z", completed=True, completed_at=None
    )
    ui.login()

    item = ui.item("예전 항목")
    expect(created(item)).to_have_text("등록 2026/10/12")
    expect(completed(item)).to_have_text("완료 -")
    expect(completed(item)).to_be_visible()


def test_checking_and_unchecking_updates_the_completion_date_at_once(ui):
    ui.server.seed("체크할 항목")
    ui.login()
    item = ui.item("체크할 항목")

    item.get_by_test_id("todo-item-checkbox").click()
    expect(completed(item)).to_have_text(f"완료 {today(ui)}")
    expect(completed(item)).to_be_visible()
    # 완료 일자는 등록 일자 아래 줄에 있다.
    assert completed(item).bounding_box()["y"] > created(item).bounding_box()["y"]

    item.get_by_test_id("todo-item-checkbox").click()
    expect(item).to_have_attribute("aria-busy", "false")
    expect(completed(item)).not_to_be_visible()
    expect(created(item)).to_have_text(f"등록 {today(ui)}")


def test_titles_start_at_the_same_position_on_every_row(ui):
    pending, done, legacy = ui.server.seed("미완료", "완료", "예전 완료")
    set_times(
        ui,
        done,
        created_at="2026-01-02T00:00:00.000000Z",
        completed=True,
        completed_at="2026-11-30T00:00:00.000000Z",
    )
    set_times(
        ui, legacy, created_at="2026-01-03T00:00:00.000000Z", completed=True, completed_at=None
    )
    ui.login()

    lefts = {
        round(ui.item(title).get_by_test_id("todo-item-title").bounding_box()["x"])
        for title in ("미완료", "완료", "예전 완료")
    }
    assert len(lefts) == 1


def test_checkbox_is_still_named_by_the_title_and_described_by_the_dates(ui):
    ui.server.seed("우유 사기")
    ui.login()

    checkbox = ui.page.get_by_role("checkbox", name="우유 사기", exact=True)
    expect(checkbox).to_have_count(1)
    expect(checkbox).to_have_accessible_description(f"등록 {today(ui)}")


def test_clicking_the_dates_toggles_like_the_rest_of_the_row(ui):
    ui.server.seed("날짜 누르기")
    ui.login()
    item = ui.item("날짜 누르기")

    created(item).click()
    expect(item.get_by_test_id("todo-item-checkbox")).to_be_checked()
    expect(completed(item)).to_have_text(f"완료 {today(ui)}")


def test_malformed_dates_are_shown_as_a_dash_and_never_as_markup(ui):
    (todo,) = ui.server.seed("이상한 날짜")
    set_times(ui, todo, created_at="<b>2026</b>", completed=True, completed_at="2026-13-45T00:00:00Z")
    ui.login()

    item = ui.item("이상한 날짜")
    expect(created(item)).to_have_text("등록 -")
    expect(completed(item)).to_have_text("완료 -")
    expect(item.locator("b")).to_have_count(0)
