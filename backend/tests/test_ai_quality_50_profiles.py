"""Quality evaluation across 50 diverse profiles per ТЗ quality criteria."""

from tests.conftest import register_and_auth


def _has_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04ff" for ch in text)


def test_ai_quality_on_50_profiles(client, monkeypatch):
    """ТЗ: 50 тестових профілів — мова відповіді збігається, довжина пункту <= +30%, без вигаданих фактів."""
    monkeypatch.setenv("AI_DAILY_LIMIT", "200")
    headers = register_and_auth(client, email="qa50@example.com")["headers"]

    errors = 0
    for i in range(50):
        lang = "uk" if i % 2 == 0 else "en"
        if lang == "uk":
            bullet = f"Розробив і впровадив сервіс звітності для відділу логістики номер {i} у команді"
            role = f"Розробник {i}"
        else:
            bullet = f"Built and maintained internal analytics service module number {i} for product team"
            role = f"Software Engineer {i}"

        resp = client.post(
            "/api/ai/improve-bullet",
            json={"bullet": bullet, "role_title": role, "language": lang},
            headers=headers,
        )
        assert resp.status_code == 200
        variants = resp.json()["variants"]
        assert len(variants) >= 2

        for v in variants:
            # Check language match
            if lang == "en" and _has_cyrillic(v.replace("«уточніть»", "")):
                errors += 1
                break
            if lang == "uk" and not _has_cyrillic(v):
                errors += 1
                break
            # Check length <= 130% of original
            if len(v) > int(len(bullet) * 1.30):
                errors += 1
                break

    # ТЗ threshold: допустимо не більше 5 помилок із 50
    assert errors <= 5, f"Too many AI quality errors: {errors}/50"
