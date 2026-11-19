"""Pytest fixtures for isolated ResumeCraft backend tests."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_resumecraft.db"
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("AI_MOCK_MODE", "true")
    monkeypatch.setenv("AI_DAILY_LIMIT", "10")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.core import database, security, storage
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def _fk(conn, _rec):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    database.engine = test_engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    security.rate_limiter._buckets.clear()
    storage.file_storage._s3_checked = True
    storage.file_storage._s3_client = None

    from app.main import app

    database.Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as test_client:
        yield test_client

    test_engine.dispose()
    get_settings.cache_clear()


def register_and_auth(client: TestClient, email: str = "test@example.com", password: str = "StrongPass123!") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "consent_accepted": True},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
        "verify_token": data["verification_token_preview"],
    }
