"""Tests for DOCX and PDF export with Cyrillic UTF-8 and AI filename formatting."""

import io

from docx import Document

from tests.conftest import register_and_auth


def test_export_docx_cyrillic_and_filename(client):
    headers = register_and_auth(client, email="docx@example.com")["headers"]

    payload = {
        "format": "docx",
        "template_id": "it",
        "language": "uk",
        "block_order": ["summary", "experience", "skills"],
        "data": {
            "contacts": {
                "first_name": "Аріна",
                "last_name": "Бадовська",
                "email": "docx@example.com",
                "phone": "+380501112233",
                "location": "Київ",
            },
            "target_role": "Python Розробник",
            "summary": "Створюю надійні веб-сервіси з підтримкою кирилиці.",
            "experiences": [
                {
                    "company": "ДУІКТ Лаб",
                    "position": "Backend Intern",
                    "start_date": "2025-02",
                    "is_current": True,
                    "bullets": ["Розробила API експорту резюме у DOCX"],
                }
            ],
            "skills": ["Python", "FastAPI", "Docker"],
        },
    }

    resp = client.post("/api/export", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["X-Export-Filename"].endswith("_Resume.docx")
    assert "Arina_Badovska" in resp.headers["X-Export-Filename"]

    doc = Document(io.BytesIO(resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Аріна Бадовська" in full_text
    assert "Python Розробник" in full_text
    assert "Розробила API експорту резюме у DOCX" in full_text


def test_export_pdf_selectable_cyrillic(client):
    headers = register_and_auth(client, email="pdf@example.com")["headers"]

    payload = {
        "format": "pdf",
        "template_id": "minimal",
        "language": "uk",
        "block_order": ["summary", "skills"],
        "data": {
            "contacts": {
                "first_name": "Олена",
                "last_name": "Коваленко",
                "email": "pdf@example.com",
            },
            "target_role": "QA Engineer",
            "summary": "Тестування веб-застосунків та автоматизація перевірок.",
            "skills": ["Pytest", "Playwright"],
        },
    }

    resp = client.post("/api/export", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["X-Export-Filename"].endswith("_Resume.pdf")
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 5000


def test_export_docx_matches_all_templates_a4_and_clean_paragraphs(client):
    headers = register_and_auth(client, email="docx.styles@example.com")["headers"]
    sample_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAP5FDvcfRYWgAAAAAElFTkSuQmCC"

    for tpl in ("minimal", "classic", "it"):
        resp = client.post(
            "/api/export",
            json={
                "format": "docx",
                "template_id": tpl,
                "language": "uk",
                "block_order": ["summary", "experience", "education", "courses", "skills", "languages", "links"],
                "data": {
                    "contacts": {
                        "first_name": "Аріна",
                        "last_name": "Бадовська",
                        "email": "docx.styles@example.com",
                        "phone": "+380687664111",
                        "location": "Київ",
                        "photo_url": sample_png,
                        "show_photo": True,
                    },
                    "target_role": "AI Prompt Engineer",
                    "summary": "Відповідальний інженер із досвідом автоматизації.",
                    "experiences": [
                        {
                            "company": "VUZOLL",
                            "position": "AI Prompt Engineer",
                            "start_date": "2026-08",
                            "is_current": True,
                            "bullets": ["Оптимізувала промпти на 35%"],
                        }
                    ],
                    "education": [
                        {
                            "institution": "ДУІКТ",
                            "degree": "Бакалавр",
                            "field_of_study": "121 Інженерія ПЗ",
                            "is_current": True,
                        }
                    ],
                    "courses": [
                        {
                            "title": "Web Design Basic",
                            "provider": "Hillel IT School",
                            "completion_date": "2025-01",
                            "certificate_url": "https://certificate.ithillel.ua/view/95232770",
                        }
                    ],
                    "skills": ["Python", "PostgreSQL"],
                    "soft_skills": ["Командна робота"],
                    "languages": [{"name": "Українська", "level": "Рідна"}],
                    "links": [{"label": "GitHub", "url": "https://github.com/AriSnowie97"}],
                },
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"{tpl}: {resp.text}"
        doc = Document(io.BytesIO(resp.content))

        # A4 dimensions (~210mm x 297mm)
        sec = doc.sections[0]
        assert 209 <= sec.page_width.mm <= 211
        assert 296 <= sec.page_height.mm <= 298

        # Education subtitle & course URL must be separate paragraphs, NEVER glued with previous text
        body_texts = [p.text for p in doc.paragraphs]
        assert any(t == "Бакалавр — 121 Інженерія ПЗ" for t in body_texts), body_texts
        assert any(t == "https://certificate.ithillel.ua/view/95232770" for t in body_texts), body_texts
        assert all("ДУІКТБакалавр" not in t for t in body_texts)
        assert all("2025-01)https://" not in t for t in body_texts)
