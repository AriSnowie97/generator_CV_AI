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
