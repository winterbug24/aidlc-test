"""상태 확인 엔드포인트 테스트 (예제 기반)."""

from __future__ import annotations


def test_health_reports_ok_without_authentication(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_exposes_no_todo_data(client, create):
    create("비공개 항목")
    assert "비공개 항목" not in client.get("/health").get_data(as_text=True)


def test_health_only_supports_get(client):
    assert client.post("/health").status_code == 405
