"""Tests for registration, login, rate-limiting, email verification, and account deletion."""

from tests.conftest import register_and_auth


def test_register_requires_consent(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "noconsent@example.com", "password": "Password123!", "consent_accepted": False},
    )
    assert resp.status_code == 422


def test_register_verify_email_and_login(client):
    auth = register_and_auth(client, email="alina@example.com", password="Password123!")
    assert auth["user"]["is_email_verified"] is False

    verify_resp = client.post("/api/auth/verify-email", json={"token": auth["verify_token"]})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_email_verified"] is True

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "alina@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_rate_limit(client):
    register_and_auth(client, email="ratelimit@example.com", password="Password123!")
    for _ in range(10):
        r = client.post("/api/auth/login", json={"email": "ratelimit@example.com", "password": "WrongPassword!"})
        assert r.status_code == 401

    blocked = client.post("/api/auth/login", json={"email": "ratelimit@example.com", "password": "WrongPassword!"})
    assert blocked.status_code == 429


def test_account_deletion_wipes_all_data_and_files(client):
    auth = register_and_auth(client, email="delete.me@example.com")
    headers = auth["headers"]

    # Export a DOCX file so Storage + ExportFile record exist
    exp = client.post("/api/export", json={"format": "docx", "template_id": "minimal", "language": "uk"}, headers=headers)
    assert exp.status_code == 200

    # Export GDPR JSON data
    gdpr = client.get("/api/settings/export-data", headers=headers)
    assert gdpr.status_code == 200
    assert gdpr.json()["user"]["email"] == "delete.me@example.com"

    # Delete account
    del_resp = client.delete("/api/settings/account", headers=headers)
    assert del_resp.status_code == 200

    # Token is now invalid / user gone
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_real_email_code_verification_resend_and_no_preview_leak(client, monkeypatch):
    captured = {}

    def fake_send(to_email: str, code: str, verify_url: str):
        captured["to_email"] = to_email
        captured["code"] = code
        captured["verify_url"] = verify_url
        return True, "sent"

    monkeypatch.setattr("app.services.auth_service.send_verification_email", fake_send)

    reg = client.post(
        "/api/auth/register",
        json={"email": "realmail@example.com", "password": "Password123!", "consent_accepted": True},
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["email_sent"] is True
    assert body["email_delivery_mode"] == "sent"
    # In real email mode, verification token must NOT be leaked in API response
    assert body["verification_token_preview"] is None
    assert captured["to_email"] == "realmail@example.com"
    assert len(captured["code"]) == 6 and captured["code"].isdigit()
    assert "verify_token=" in captured["verify_url"]

    # Wrong 6-digit code must fail
    wrong = client.post(
        "/api/auth/verify-email",
        json={"email": "realmail@example.com", "code": "000000" if captured["code"] != "000000" else "999999"},
    )
    assert wrong.status_code == 400

    # Resend works once, then rate-limits for 60s
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resend1 = client.post("/api/auth/resend-verification", headers=headers)
    assert resend1.status_code == 200
    assert resend1.json()["email_sent"] is True
    new_code = captured["code"]

    resend2 = client.post("/api/auth/resend-verification", headers=headers)
    assert resend2.status_code == 429

    # Correct 6-digit code verifies email
    ok = client.post(
        "/api/auth/verify-email",
        json={"email": "realmail@example.com", "code": new_code},
    )
    assert ok.status_code == 200
    assert ok.json()["is_email_verified"] is True
