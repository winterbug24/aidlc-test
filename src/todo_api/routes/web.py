"""할 일 화면 제공.

의도적 공개: 이 묶음은 인증 없이 열린다. 제공하는 것은 데이터와 API 키가 들어 있지 않은
화면 파일뿐이며, 할 일 데이터는 화면의 스크립트가 API 키로 /todos를 호출해 가져온다.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, send_from_directory

from todo_api.errors import NotFound

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
INDEX = ("index.html", "text/html; charset=utf-8")
# 제공하는 파일은 이 목록이 전부다. 요청 경로를 파일 시스템 경로로 쓰지 않는다.
ASSETS: dict[str, tuple[str, str]] = {
    "app.css": ("app.css", "text/css; charset=utf-8"),
    "app.js": ("app.js", "text/javascript; charset=utf-8"),
}

bp = Blueprint("web", __name__, url_prefix="/api_test")


def _send(entry: tuple[str, str]):
    filename, content_type = entry
    response = send_from_directory(WEB_DIR, filename, conditional=False)
    response.headers["Content-Type"] = content_type
    return response


@bp.get("", strict_slashes=False)
def index():
    return _send(INDEX)


@bp.get("/<name>")
def asset(name: str):
    entry = ASSETS.get(name)
    if entry is None:
        raise NotFound()
    return _send(entry)
