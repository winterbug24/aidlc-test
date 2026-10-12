"""재사용 가능한 Hypothesis 제너레이터 (도메인 제약을 반영)."""

from __future__ import annotations

import string
from datetime import timezone

from hypothesis import strategies as st

from todo_api.serialization import Todo
from todo_api.validation import TITLE_MAX_LENGTH

_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_ASCII_SWAP = str.maketrans(
    string.ascii_uppercase + string.ascii_lowercase,
    string.ascii_lowercase + string.ascii_uppercase,
)
# 저장할 수 있는 문자: 제어 문자(Cc)와 서로게이트(Cs)를 뺀 모든 유니코드
_TITLE_ALPHABET = st.characters(exclude_categories=("Cc", "Cs"))
_PADDING = st.text(alphabet=" \t\n 　", max_size=3)
_CONTROL_CHARS = st.sampled_from(["\x00", "\x07", "\x1b", "\x7f", "\n", "\t", "\x85"])


def ascii_fold(title: str) -> str:
    """중복 판정과 같은 기준: 영문 A~Z만 소문자로 바꾼다."""
    return title.translate(_ASCII_LOWER)


def ascii_swapcase(title: str) -> str:
    return title.translate(_ASCII_SWAP)


def valid_titles() -> st.SearchStrategy[str]:
    """정규화된 유효 제목: 앞뒤 공백 없음, 1~200자, 한글 등 유니코드 포함."""
    return (
        st.text(alphabet=_TITLE_ALPHABET, min_size=1, max_size=TITLE_MAX_LENGTH)
        .map(str.strip)
        .filter(bool)
    )


def padded_titles() -> st.SearchStrategy[tuple[str, str]]:
    """(앞뒤 공백이 붙은 입력, 기대하는 정규화 결과) 쌍."""
    return st.builds(
        lambda left, core, right: (left + core + right, core),
        _PADDING,
        valid_titles(),
        _PADDING,
    )


def invalid_titles() -> st.SearchStrategy[str]:
    """거부되어야 하는 제목: 공백뿐, 너무 김, 제어 문자 포함."""
    blank = st.text(alphabet=" \t\n　", max_size=10)
    too_long = st.text(
        alphabet=st.characters(categories=("Lu", "Ll", "Lo", "Nd")),
        min_size=TITLE_MAX_LENGTH + 1,
        max_size=TITLE_MAX_LENGTH + 50,
    )
    short = st.text(alphabet=st.characters(categories=("Ll", "Lo")), min_size=1, max_size=20)
    with_control = st.builds(lambda a, c, b: a + c + b, short, _CONTROL_CHARS, short)
    return st.one_of(blank, too_long, with_control)


def unique_titles(max_size: int = 8) -> st.SearchStrategy[list[str]]:
    """서로 중복되지 않는(대소문자 무시) 제목 목록."""
    return st.lists(valid_titles(), unique_by=ascii_fold, max_size=max_size)


def todos() -> st.SearchStrategy[Todo]:
    created_at = st.datetimes(timezones=st.just(timezone.utc)).map(
        lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    return st.builds(
        Todo,
        id=st.integers(min_value=1, max_value=2**63 - 1),
        title=valid_titles(),
        completed=st.booleans(),
        created_at=created_at,
    )
