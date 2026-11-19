"""Tests for resume editor, 3 templates, block order persistence, and XSS escaping."""

from tests.conftest import register_and_auth


def test_template_switching_and_block_order_persistence(client):
    headers = register_and_auth(client, email="editor@example.com")["headers"]

    custom_order = ["skills", "experience", "summary", "education", "languages", "links"]
    data_payload = {
        "contacts": {"first_name": "Іван", "last_name": "Петренко", "email": "editor@example.com"},
        "target_role": "Frontend Developer",
        "summary": "React та TypeScript розробник.",
        "skills": ["React", "TypeScript", "Next.js"],
    }

    save_resp = client.put(
        "/api/resume",
        json={
            "title": "Frontend CV",
            "template_id": "it",
            "language": "uk",
            "block_order": custom_order,
            "data": data_payload,
        },
        headers=headers,
    )
    assert save_resp.status_code == 200

    # Switch template to classic without losing data
    switch_resp = client.put(
        "/api/resume",
        json={
            "title": "Frontend CV",
            "template_id": "classic",
            "language": "uk",
            "block_order": custom_order,
            "data": data_payload,
        },
        headers=headers,
    )
    assert switch_resp.status_code == 200

    # Reload via GET and verify block order + data remained intact
    get_resp = client.get("/api/resume", headers=headers)
    assert get_resp.status_code == 200
    loaded = get_resp.json()
    assert loaded["template_id"] == "classic"
    assert loaded["block_order"] == custom_order
    assert loaded["data"]["target_role"] == "Frontend Developer"
    assert loaded["data"]["skills"] == ["React", "TypeScript", "Next.js"]


def test_guest_preview_escapes_xss_and_supports_all_templates(client):
    for tpl in ("minimal", "classic", "it"):
        resp = client.post(
            "/api/resume/preview-html",
            json={
                "template_id": tpl,
                "language": "uk",
                "block_order": ["summary", "skills"],
                "data": {
                    "contacts": {"full_name": "<script>alert(1)</script>Олег"},
                    "summary": "Тестовий опис",
                    "skills": ["Python"],
                },
            },
        )
        assert resp.status_code == 200
        assert "<script>alert(1)</script>" not in resp.text
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text
        # ATS rule: no layout tables
        assert "<table" not in resp.text


def test_builtin_web_ui_and_health(client):
    ui_resp = client.get("/")
    assert ui_resp.status_code == 200
    assert "ResumeCraft" in ui_resp.text

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
