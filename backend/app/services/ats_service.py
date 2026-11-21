"""Deterministic ATS (Applicant Tracking System) readiness & keyword analyzer."""

import re
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeLanguage, TemplateId
from app.services.resume_service import estimate_pages

STOPWORDS = {
    # English
    "the", "and", "for", "with", "that", "this", "from", "your", "will", "have", "are", "our", "you",
    "work", "team", "role", "experience", "years", "skills", "about", "into", "using", "strong", "good",
    "ability", "knowledge", "working", "requirements", "responsibilities", "must", "plus", "nice", "high",
    "level", "english", "remote", "office", "hybrid", "company", "product", "project", "projects",
    # Ukrainian
    "для", "та", "або", "про", "при", "від", "під", "над", "без", "через", "після", "перед", "між",
    "досвід", "роботи", "робота", "команді", "команда", "знання", "вміння", "навички", "вимоги",
    "обов", "язки", "умови", "буде", "плюсом", "рівень", "віддалено", "офіс", "компанія", "проєкт",
    "проєктів", "посада", "шукаємо", "потрібен", "потрібна", "нашої", "нашого", "який", "яка", "які",
}

TECH_TOKEN_RE = re.compile(r"\b[A-Za-zА-Яа-яІіЇїЄєҐґ][A-Za-zА-Яа-яІіЇїЄєҐґ0-9+#./-]{1,28}\b")
METRIC_RE = re.compile(r"(?:\d+%|\$\d+|\d+\+|\d+\s*(?:раз|x|х|к|k|міс|рок|user|client|корист|клієнт|год|дн|ms|мс|с))", re.I)


class ATSCheckItem(BaseModel):
    key: str
    label: str
    passed: bool
    tip: str


class ATSCheckRequest(BaseModel):
    data: ProfileData
    template_id: TemplateId = "minimal"
    language: ResumeLanguage = "uk"
    vacancy_text: Optional[str] = Field(default="", max_length=6000)


class ATSCheckResponse(BaseModel):
    score: int
    grade: str
    estimated_pages: int
    checks: list[ATSCheckItem]
    matched_keywords: list[str]
    missing_keywords: list[str]


def _extract_resume_corpus(data: ProfileData) -> str:
    parts = [
        data.target_role,
        data.summary,
        " ".join(data.skills),
        " ".join(f"{l.name} {l.level}" for l in data.languages),
    ]
    for exp in data.experiences:
        parts.extend([exp.position, exp.company, *exp.bullets])
    for edu in data.education:
        parts.extend([edu.institution, edu.degree, edu.field_of_study])
    return " ".join(p for p in parts if p).lower()


def _extract_vacancy_keywords(vacancy_text: str) -> list[str]:
    """Extract meaningful candidate keywords from vacancy text (treated strictly as data)."""
    if not vacancy_text or not vacancy_text.strip():
        return []
    freq: dict[str, tuple[str, int]] = {}
    for match in TECH_TOKEN_RE.findall(vacancy_text):
        clean = match.strip(".,;:-/()")
        low = clean.lower()
        if len(low) < 2 or low in STOPWORDS or low.isdigit():
            continue
        # Prioritize technical/domain terms (ASCII tech words or longer domain words)
        is_ascii_tech = bool(re.match(r"^[a-z0-9+#./-]+$", low)) and len(low) >= 2
        if not is_ascii_tech and len(low) < 5:
            continue
        prev_label, prev_count = freq.get(low, (clean, 0))
        freq[low] = (prev_label, prev_count + 1)

    ranked = sorted(freq.items(), key=lambda kv: (-kv[1][1], -len(kv[0])))
    return [label for _, (label, _) in ranked[:20]]


def analyze_ats(req: ATSCheckRequest) -> ATSCheckResponse:
    """Compute transparent ATS readiness score and actionable recommendations."""
    data = req.data
    pages, page_warning = estimate_pages(data)

    has_name = bool(data.contacts.full_name.strip() or (data.contacts.first_name.strip() and data.contacts.last_name.strip()))
    has_email = bool(str(data.contacts.email or "").strip())
    has_phone = bool(data.contacts.phone.strip())
    contacts_ok = has_name and has_email and has_phone

    role_ok = len(data.target_role.strip()) >= 3

    summary_len = len(data.summary.strip())
    summary_ok = 60 <= summary_len <= 650

    all_bullets = [b.strip() for exp in data.experiences for b in exp.bullets if len(b.strip()) >= 12]
    exp_ok = len(data.experiences) >= 1 and len(all_bullets) >= 1

    edu_ok = any(bool(e.institution.strip()) for e in data.education)

    has_metrics = any(METRIC_RE.search(b) or any(ch.isdigit() for ch in b) for b in all_bullets)

    skills_count = len([s for s in data.skills if s.strip()])
    skills_ok = 5 <= skills_count <= 30

    filled_core_sections = sum(
        [
            contacts_ok,
            summary_ok,
            exp_ok,
            edu_ok,
            skills_count >= 1,
        ]
    )
    length_ok = (not page_warning) and filled_core_sections >= 4

    checks = [
        ATSCheckItem(
            key="contacts",
            label="Контакти у чистому тексті",
            passed=contacts_ok,
            tip="Вкажіть ім'я, email і телефон — ATS зчитує їх першими."
            if not contacts_ok
            else "Ім'я, email і телефон коректно зчитуються ATS.",
        ),
        ATSCheckItem(
            key="target_role",
            label="Чітка назва посади",
            passed=role_ok,
            tip="Додайте цільову посаду (напр. Junior Python Developer) — за нею рекрутери фільтрують резюме."
            if not role_ok
            else "Цільова посада вказана чітко.",
        ),
        ATSCheckItem(
            key="summary",
            label="Збалансований блок «Про себе»",
            passed=summary_ok,
            tip="Напишіть 2–4 змістовні речення (60–650 символів) із ключовими технологіями та фокусом."
            if not summary_ok
            else "Довжина та структура «Про себе» оптимальні для ATS.",
        ),
        ATSCheckItem(
            key="experience",
            label="Досвід зі списком досягнень",
            passed=exp_ok,
            tip="Додайте щонайменше 1 місце досвіду або навчальний проєкт і змістовні пункти досягнень."
            if not exp_ok
            else f"Знайдено {len(data.experiences)} запис(и) досвіду та {len(all_bullets)} пункт(ів) досягнень.",
        ),
        ATSCheckItem(
            key="education",
            label="Заповнений блок «Освіта»",
            passed=edu_ok,
            tip="Додайте заклад освіти, спеціальність або курси — ATS часто перевіряє наявність секції «Освіта»."
            if not edu_ok
            else "Блок «Освіта» заповнено коректно.",
        ),
        ATSCheckItem(
            key="metrics",
            label="Цифри та вимірювані результати",
            passed=has_metrics,
            tip="Додайте конкретні цифри/метрики в досягнення (%, час, кількість) або скористайтеся AI-кнопкою."
            if not has_metrics
            else "У досягненнях є кількісні показники — це суттєво підвищує рейтинг.",
        ),
        ATSCheckItem(
            key="skills",
            label="Ключові навички (5–30)",
            passed=skills_ok,
            tip=f"Зараз вказано {skills_count} навичок. Додайте хоча б 5 релевантних ключових слів."
            if not skills_ok
            else f"Додано {skills_count} структурованих навичок для пошуку за ключовими словами.",
        ),
        ATSCheckItem(
            key="structure_length",
            label="Повна ATS-структура та обсяг (1–2 стор.)",
            passed=length_ok,
            tip=(
                "Скоротіть резюме до 1–2 сторінок A4."
                if page_warning
                else f"Заповнено {filled_core_sections}/5 основних секцій. Заповніть щонайменше 4 секції (контакти, про себе, досвід, освіта, навички)."
            )
            if not length_ok
            else f"Одноколонкова структура без таблиць, {filled_core_sections}/5 секцій, обсяг {pages} стор. A4 — ідеально для ATS.",
        ),
    ]

    weights = {
        "contacts": 15,
        "target_role": 10,
        "summary": 12,
        "experience": 16,
        "education": 12,
        "metrics": 10,
        "skills": 15,
        "structure_length": 10,
    }
    base_score = sum(weights[c.key] for c in checks if c.passed)

    matched: list[str] = []
    missing: list[str] = []
    keywords = _extract_vacancy_keywords(req.vacancy_text or "")
    if keywords:
        corpus = _extract_resume_corpus(data)
        for kw in keywords:
            if kw.lower() in corpus:
                matched.append(kw)
            else:
                missing.append(kw)
        kw_ratio = len(matched) / max(1, len(keywords))
        # Blend base ATS structure score (75%) + keyword match (25%) when vacancy text is provided
        score = int(round(base_score * 0.75 + (kw_ratio * 100) * 0.25))
    else:
        score = base_score

    if score >= 85:
        grade = "Відмінно для ATS"
    elif score >= 65:
        grade = "Добре, але можна підсилити"
    else:
        grade = "Потребує доопрацювання"

    return ATSCheckResponse(
        score=score,
        grade=grade,
        estimated_pages=pages,
        checks=checks,
        matched_keywords=matched,
        missing_keywords=missing,
    )
