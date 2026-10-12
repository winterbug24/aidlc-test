"""상태 확인 엔드포인트. 의도적으로 공개이며 할 일 데이터를 반환하지 않는다."""

from __future__ import annotations

import sqlite3

from flask import Blueprint, jsonify

from todo_api.db import get_db
from todo_api.errors import ServiceUnavailable

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    try:
        get_db().execute("SELECT 1 FROM todos LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        raise ServiceUnavailable() from exc
    return jsonify({"status": "ok"})
