"""Tests for profile validation rules defined in ТЗ."""

from tests.conftest import register_and_auth


def test_profile_validation_rules(client):
    headers = register_and_auth(client, email="val@example.com")["headers"]

    # Invalid phone
    r_phone = client.put(
        "/api/profile",
        json={"contacts": {"full_name": "Аріна Бадовська", "email": "val@example.com", "phone": "abc"}},
        headers=headers,
    )
    assert r_phone.status_code == 422

    # End date earlier than start date
    r_dates = client.put(
        "/api/profile",
        json={
            "experiences": [
                {
                    "company": "DUICT",
                    "position": "Developer",
                    "start_date": "2025-05",
                    "end_date": "2024-01",
                    "is_current": False,
                }
            ]
        },
        headers=headers,
    )
    assert r_dates.status_code == 422

    # More than 15 experiences
    too_many_exp = [
        {"company": f"Comp {i}", "position": "Dev", "start_date": "2020-01", "is_current": True}
        for i in range(16)
    ]
    r_exp = client.put("/api/profile", json={"experiences": too_many_exp}, headers=headers)
    assert r_exp.status_code == 422

    # More than 30 skills
    r_skills = client.put("/api/profile", json={"skills": [f"Skill {i}" for i in range(31)]}, headers=headers)
    assert r_skills.status_code == 422


def test_profile_completeness_updates(client):
    headers = register_and_auth(client, email="comp@example.com")["headers"]
    payload = {
        "contacts": {
            "first_name": "Аріна",
            "last_name": "Бадовська",
            "email": "comp@example.com",
            "phone": "+380501234567",
            "location": "Київ",
        },
        "target_role": "Python Backend Developer",
        "summary": "Розробниця з досвідом створення веб-сервісів.",
        "experiences": [
            {
                "company": "TechUA",
                "position": "Junior Python Developer",
                "start_date": "2024-01",
                "is_current": True,
                "bullets": ["Розробила REST API на FastAPI"],
            }
        ],
        "education": [{"institution": "ДУІКТ", "degree": "Бакалавр", "start_date": "2023-09", "is_current": True}],
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "languages": [{"name": "Українська", "level": "Рідна"}],
        "links": [{"label": "GitHub", "url": "https://github.com/example"}],
    }
    resp = client.put("/api/profile", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["completeness_score"] == 100
    assert resp.json()["missing_blocks"] == []
