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
