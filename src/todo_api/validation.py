"""엔드포인트별 입력 스키마와 검증 함수.

요청 객체에 의존하지 않는 순수 함수로 두어 단독으로 테스트할 수 있게 한다.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from todo_api.errors import ValidationError

TITLE_MAX_LENGTH = 200
# 제어 문자(Cc)와 짝이 맞지 않는 서로게이트(Cs)는 저장하지 않는다.
_FORBIDDEN_CATEGORIES = ("Cc", "Cs")


class FieldError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class FieldSpec:
    required: bool
    parse: Callable[[Any], Any]


def normalize_title(value: Any) -> str:
    """제목을 검증하고 앞뒤 공백을 제거한 값을 돌려준다."""
    if not isinstance(value, str):
        raise FieldError("invalid_type")
    title = value.strip()
    if not title:
        raise FieldError("too_short")
    if len(title) > TITLE_MAX_LENGTH:
        raise FieldError("too_long")
    if any(unicodedata.category(ch) in _FORBIDDEN_CATEGORIES for ch in title):
        raise FieldError("invalid_characters")
    return title


def parse_completed_flag(value: Any) -> bool:
    """JSON 불리언만 허용한다. 1, "true" 등은 거부한다."""
    if not isinstance(value, bool):
        raise FieldError("invalid_type")
    return value


def parse_completed_query(value: Any) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise FieldError("invalid_value")


CREATE_TODO_SCHEMA: Mapping[str, FieldSpec] = {
    "title": FieldSpec(required=True, parse=normalize_title),
}
UPDATE_TODO_SCHEMA: Mapping[str, FieldSpec] = {
    "completed": FieldSpec(required=True, parse=parse_completed_flag),
}
LIST_QUERY_SCHEMA: Mapping[str, FieldSpec] = {
    "completed": FieldSpec(required=False, parse=parse_completed_query),
}


def validate_object(data: Any, schema: Mapping[str, FieldSpec]) -> dict[str, Any]:
    """스키마로 객체를 검증한다. 문제는 모두 모아 한 번에 알린다."""
    if not isinstance(data, dict):
        raise ValidationError(
            "요청 본문은 JSON 객체여야 합니다.",
            details=[{"field": "body", "reason": "invalid_type"}],
        )

    details: list[dict[str, str]] = []
    unknown = sorted(str(key) for key in data if key not in schema)
    details.extend({"field": key, "reason": "unknown_field"} for key in unknown)

    cleaned: dict[str, Any] = {}
    for name, spec in schema.items():
        if name not in data:
            if spec.required:
                details.append({"field": name, "reason": "required"})
            continue
        try:
            cleaned[name] = spec.parse(data[name])
        except FieldError as exc:
            details.append({"field": name, "reason": exc.reason})

    if details:
        message = (
            "요청에 허용되지 않는 필드가 있습니다."
            if unknown
            else ValidationError.message
        )
        raise ValidationError(message, details=details)
    return cleaned
