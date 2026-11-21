"""Tests for resume editor, 3 templates, block order persistence, and XSS escaping."""

from tests.conftest import register_and_auth


def test_template_switching_and_block_order_persistence(client):
    headers = register_and_auth(client, email="editor@example.com")["headers"]

    custom_order = ["skills", "experience", "courses", "summary", "education", "languages", "links"]
    data_payload = {
        "contacts": {"first_name": "Іван", "last_name": "Петренко", "email": "editor@example.com"},
        "target_role": "Frontend Developer",
        "summary": "React та TypeScript розробник.",
        "courses": [
            {
                "title": "Prompt Engineering",
                "provider": "DeepLearning.AI",
                "completion_date": "2025-10",
            }
        ],
        "skills": ["React", "TypeScript", "Next.js"],
        "soft_skills": ["Командна робота", "Критичне мислення"],
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
    assert loaded["data"]["soft_skills"] == ["Командна робота", "Критичне мислення"]
    assert loaded["data"]["courses"][0]["title"] == "Prompt Engineering"

    prev = client.post(
        "/api/resume/preview-html",
        json={"template_id": "it", "language": "uk", "block_order": custom_order, "data": loaded["data"]},
    )
    assert prev.status_code == 200
    assert "Курси та сертифікати" in prev.text
    assert "Prompt Engineering" in prev.text
    assert "Hard Skills" in prev.text
    assert "Soft Skills" in prev.text
    assert "Командна робота" in prev.text


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


def test_ats_check_endpoint_and_vacancy_keywords(client):
    payload = {
        "template_id": "minimal",
        "language": "uk",
        "vacancy_text": "Looking for Junior Python Developer with FastAPI, PostgreSQL, Docker, Kubernetes experience.",
        "data": {
            "contacts": {
                "first_name": "Аріна",
                "last_name": "Бадовська",
                "email": "arina@example.com",
                "phone": "+380671234567",
            },
            "target_role": "Junior Python Developer",
            "summary": "Розробниця з практичним досвідом створення REST API на FastAPI та PostgreSQL для веб-сервісів.",
            "experiences": [
                {
                    "company": "DUICT Lab",
                    "position": "Backend Developer",
                    "start_date": "2025-01",
                    "is_current": True,
                    "bullets": ["Прискорила обробку запитів на 40% та покрила код 14 автотестами"],
                }
            ],
            "education": [
                {
                    "institution": "ДУІКТ",
                    "degree": "Бакалавр",
                    "field_of_study": "Інформаційні технології",
                    "start_date": "2023-09",
                    "is_current": True,
                }
            ],
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        },
    }
    resp = client.post("/api/resume/ats-check", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] >= 85
    assert len(body["checks"]) == 9
    assert any(k.lower() == "fastapi" for k in body["matched_keywords"])
    assert any(k.lower() == "kubernetes" for k in body["missing_keywords"])

    # Verify ATS photo warning & show_photo toggle
    sample_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    with_photo = {
        "data": {**payload["data"], "contacts": {**payload["data"]["contacts"], "photo_url": sample_png, "show_photo": True}}
    }
    res_photo_on = client.post("/api/resume/ats-check", json=with_photo)
    assert res_photo_on.status_code == 200
    photo_chk_on = next(c for c in res_photo_on.json()["checks"] if c["key"] == "photo_ats")
    assert photo_chk_on["passed"] is False

    prev_on = client.post("/api/resume/preview-html", json={"template_id": "minimal", "language": "uk", "data": with_photo["data"]})
    assert "<img class=\"cv-photo\"" in prev_on.text

    with_photo_hidden = {
        "data": {**payload["data"], "contacts": {**payload["data"]["contacts"], "photo_url": sample_png, "show_photo": False}}
    }
    res_photo_off = client.post("/api/resume/ats-check", json=with_photo_hidden)
    assert res_photo_off.status_code == 200
    photo_chk_off = next(c for c in res_photo_off.json()["checks"] if c["key"] == "photo_ats")
    assert photo_chk_off["passed"] is True
    assert res_photo_off.json()["score"] == res_photo_on.json()["score"] + 5

    prev_off = client.post("/api/resume/preview-html", json={"template_id": "minimal", "language": "uk", "data": with_photo_hidden["data"]})
    assert "<img class=\"cv-photo\"" not in prev_off.text

    # Sparse resume without education, skills, or bullets must score honestly low (< 45)
    sparse = client.post(
        "/api/resume/ats-check",
        json={
            "data": {
                "contacts": {"first_name": "Аріна", "last_name": "Бадовська", "email": "a@b.com", "phone": "+380681112233"},
                "target_role": "AI Prompt Engineer",
                "summary": "Відповідальний спеціаліст із досвідом роботи над прикладними задачами та проєктами.",
                "experiences": [{"company": "Vuzoll", "position": "AI Prompt Engineer", "bullets": [""]}],
            }
        },
    )
    assert sparse.status_code == 200
    assert sparse.json()["score"] <= 45


def test_resume_auto_translation_uk_to_en_and_pii_safety(client):
    payload = {
        "source_language": "uk",
        "target_language": "en",
        "data": {
            "contacts": {
                "first_name": "Аріна",
                "last_name": "Бадовська",
                "full_name": "Аріна Бадовська",
                "email": "arina@example.com",
                "phone": "+380671234567",
                "location": "Київ, Україна",
            },
            "target_role": "Junior Python Developer",
            "summary": "Студентка ІТ-напряму.",
            "desired_salary": "від $800",
            "work_format": "Гібрид / Віддалено",
            "education": [
                {
                    "institution": "Державний університет інформаційно-комунікаційних технологій",
                    "degree": "Бакалавр",
                    "field_of_study": "Інформаційні технології",
                    "start_date": "2023-09",
                    "is_current": True,
                }
            ],
            "skills": ["Python", "FastAPI", "Docker"],
            "soft_skills": ["Командна робота", "Тайм-менеджмент"],
            "languages": [{"name": "Українська", "level": "Рідна"}],
        },
    }
    resp = client.post("/api/resume/translate", json=payload)
    assert resp.status_code == 200, resp.text
    out = resp.json()["data"]
    assert out["contacts"]["first_name"] == "Arina"
    assert out["contacts"]["last_name"] == "Badovska"
    assert out["contacts"]["email"] == "arina@example.com"
    assert out["contacts"]["phone"] == "+380671234567"
    assert out["contacts"]["location"] == "Kyiv, Ukraine"
    assert out["work_format"] == "Hybrid / Remote"
    assert out["desired_salary"] == "from $800"
    assert out["education"][0]["degree"] == "Bachelor's Degree"
    assert out["skills"] == ["Python", "FastAPI", "Docker"]
    assert out["soft_skills"] == ["Teamwork", "Time management"]
    assert out["languages"][0]["name"] == "Ukrainian"
    assert out["languages"][0]["level"] == "Native"
