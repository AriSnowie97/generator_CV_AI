"""Tests for AI daily quota, dynamic config reload, and PII protection."""

from pathlib import Path

from tests.conftest import register_and_auth


def test_ai_daily_limit_and_dynamic_config(client, tmp_path: Path, monkeypatch):
    headers = register_and_auth(client, email="ai@example.com")["headers"]

    # Default limit = 10
    q_resp = client.get("/api/ai/quota", headers=headers)
    assert q_resp.status_code == 200
    assert q_resp.json()["daily_limit"] == 10
    assert q_resp.json()["remaining_today"] == 10

    # Dynamically override via env without code release
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    for _ in range(2):
        ok = client.post(
            "/api/ai/improve-bullet",
            json={"bullet": "Розробив модуль авторизації для користувачів", "language": "uk"},
            headers=headers,
        )
        assert ok.status_code == 200
        assert len(ok.json()["variants"]) >= 2

    # 3rd request must return 429 with clear Ukrainian reset message
    exhausted = client.post(
        "/api/ai/improve-bullet",
        json={"bullet": "Ще один пункт досвіду для тестування ліміту", "language": "uk"},
        headers=headers,
    )
    assert exhausted.status_code == 429
    assert "ліміт" in exhausted.json()["detail"].lower()


def test_ai_pii_stripping():
    from app.services.ai_service import strip_pii

    raw = "Зв'язок зі мною: test.user@gmail.com або +380 50 123 45 67 щодо проєкту"
    cleaned = strip_pii(raw)
    assert "test.user@gmail.com" not in cleaned
    assert "+380 50 123 45 67" not in cleaned
    assert "[email]" in cleaned
    assert "[phone]" in cleaned
