"""ATS-friendly HTML templates (minimal, classic, it) without layout tables."""

import html
from typing import Literal

from app.schemas.profile import ProfileData

SECTION_TITLES = {
    "uk": {
        "summary": "Про себе",
        "experience": "Досвід роботи",
        "education": "Освіта",
        "skills": "Навички",
        "languages": "Мови",
        "links": "Посилання",
        "present": "дотепер",
        "salary": "Бажана зарплата",
        "format": "Формат роботи",
    },
    "en": {
        "summary": "Summary",
        "experience": "Experience",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "links": "Links",
        "present": "Present",
        "salary": "Desired salary",
        "format": "Work format",
    },
}


def _e(value: str | None) -> str:
    return html.escape((value or "").strip())


def _display_name(data: ProfileData) -> str:
    if data.contacts.full_name.strip():
        return data.contacts.full_name.strip()
    combined = f"{data.contacts.first_name.strip()} {data.contacts.last_name.strip()}".strip()
    return combined or "ResumeCraft Candidate"


def _format_dates(start: str, end: str, is_current: bool, present_label: str) -> str:
    s = (start or "").strip()
    e = present_label if is_current else (end or "").strip()
    if s and e:
        return f"{s} — {e}"
    return s or e


def _render_section(block_key: str, data: ProfileData, labels: dict[str, str]) -> str:
    if block_key == "summary":
        if not data.summary.strip():
            return ""
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['summary'])}</h2>
            <p class="summary-text">{_e(data.summary)}</p>
        </section>
        """

    if block_key == "experience":
        if not data.experiences:
            return ""
        items_html = []
        for exp in data.experiences:
            dates = _format_dates(exp.start_date, exp.end_date, exp.is_current, labels["present"])
            bullets = "".join(f"<li>{_e(b)}</li>" for b in exp.bullets if b.strip())
            bullets_html = f"<ul>{bullets}</ul>" if bullets else ""
            items_html.append(
                f"""
                <article class="cv-item">
                    <div class="cv-item-header">
                        <div class="cv-item-title"><strong>{_e(exp.position)}</strong>{(' · ' + _e(exp.company)) if exp.company else ''}</div>
                        <div class="cv-item-dates">{_e(dates)}</div>
                    </div>
                    {bullets_html}
                </article>
                """
            )
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['experience'])}</h2>
            {''.join(items_html)}
        </section>
        """

    if block_key == "education":
        if not data.education:
            return ""
        items_html = []
        for edu in data.education:
            dates = _format_dates(edu.start_date, edu.end_date, edu.is_current, labels["present"])
            degree_part = " — ".join(p for p in (_e(edu.degree), _e(edu.field_of_study)) if p)
            items_html.append(
                f"""
                <article class="cv-item">
                    <div class="cv-item-header">
                        <div class="cv-item-title"><strong>{_e(edu.institution)}</strong></div>
                        <div class="cv-item-dates">{_e(dates)}</div>
                    </div>
                    {f'<p class="muted">{degree_part}</p>' if degree_part else ''}
                </article>
                """
            )
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['education'])}</h2>
            {''.join(items_html)}
        </section>
        """

    if block_key == "skills":
        if not data.skills:
            return ""
        chips = "".join(f"<span class='skill-tag'>{_e(s)}</span>" for s in data.skills if s.strip())
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['skills'])}</h2>
            <div class="skills-list">{chips}</div>
        </section>
        """

    if block_key == "languages":
        if not data.languages:
            return ""
        items = "".join(
            f"<li><strong>{_e(l.name)}</strong>{(' — ' + _e(l.level)) if l.level else ''}</li>"
            for l in data.languages
            if l.name.strip()
        )
        if not items:
            return ""
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['languages'])}</h2>
            <ul class="inline-list">{items}</ul>
        </section>
        """

    if block_key == "links":
        if not data.links:
            return ""
        items = "".join(
            f"<li><strong>{_e(lnk.label or 'Link')}:</strong> {_e(lnk.url)}</li>"
            for lnk in data.links
            if lnk.url.strip()
        )
        if not items:
            return ""
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['links'])}</h2>
            <ul class="inline-list">{items}</ul>
        </section>
        """

    return ""


def _template_css(template_id: Literal["minimal", "classic", "it"]) -> str:
    base = """
    @page { size: A4; margin: 16mm 18mm; }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        padding: 0;
        color: #18181b;
        line-height: 1.45;
        font-size: 10.5pt;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    h1 { margin: 0 0 4px 0; font-size: 21pt; line-height: 1.15; }
    .target-role { font-size: 12pt; margin: 0 0 8px 0; }
    .contacts-line { font-size: 9.5pt; color: #3f3f46; display: flex; flex-wrap: wrap; gap: 6px 14px; }
    .cv-section { margin-top: 14px; page-break-inside: avoid; }
    .cv-section h2 { font-size: 11.5pt; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.04em; }
    .cv-item { margin-bottom: 9px; }
    .cv-item-header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
    .cv-item-dates { font-size: 9.5pt; color: #52525b; white-space: nowrap; }
    ul { margin: 4px 0 0 18px; padding: 0; }
    li { margin-bottom: 3px; }
    p { margin: 3px 0; }
    .muted { color: #52525b; font-size: 9.5pt; }
    .skills-list { display: flex; flex-wrap: wrap; gap: 6px; }
    .inline-list { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 16px; }
    """

    if template_id == "classic":
        return base + """
        body { font-family: Georgia, "Times New Roman", "Liberation Serif", serif; }
        .cv-header { text-align: center; border-bottom: 1.5px solid #1e293b; padding-bottom: 10px; }
        .contacts-line { justify-content: center; }
        .target-role { color: #334155; font-style: italic; }
        .cv-section h2 { border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; color: #0f172a; }
        .skill-tag { font-size: 9.5pt; padding-right: 8px; }
        .skill-tag:not(:last-child)::after { content: " •"; color: #64748b; }
        """

    if template_id == "it":
        return base + """
        body { font-family: "Segoe UI", Arial, "Liberation Sans", sans-serif; }
        .cv-header { border-left: 4px solid #2563eb; padding-left: 12px; margin-bottom: 6px; }
        h1 { color: #0f172a; }
        .target-role { color: #2563eb; font-weight: 600; }
        .cv-section h2 { color: #1d4ed8; border-bottom: 1px solid #dbeafe; padding-bottom: 3px; }
        .skill-tag {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 9pt;
            font-family: "Cascadia Code", Consolas, "Liberation Mono", monospace;
        }
        """

    # minimal (default)
    return base + """
    body { font-family: "Segoe UI", Arial, "Liberation Sans", sans-serif; }
    .cv-header { border-bottom: 1px solid #e4e4e7; padding-bottom: 10px; }
    .target-role { color: #3f3f46; font-weight: 500; }
    .cv-section h2 { color: #18181b; border-bottom: 1px solid #f4f4f5; padding-bottom: 2px; }
    .skill-tag { background: #f4f4f5; color: #18181b; border-radius: 3px; padding: 2px 7px; font-size: 9.2pt; }
    """


def render_resume_html(
    data: ProfileData,
    template_id: Literal["minimal", "classic", "it"],
    language: Literal["uk", "en"],
    block_order: list[str],
) -> str:
    """Render complete standalone UTF-8 HTML document for PDF export or preview."""
    labels = SECTION_TITLES.get(language, SECTION_TITLES["uk"])
    name = _display_name(data)
    contact_parts = [
        p
        for p in (
            str(data.contacts.email or "").strip(),
            data.contacts.phone.strip(),
            data.contacts.location.strip(),
            f"{labels['format']}: {data.work_format.strip()}" if data.work_format.strip() else "",
            f"{labels['salary']}: {data.desired_salary.strip()}" if data.desired_salary.strip() else "",
        )
        if p
    ]
    contacts_html = "".join(f"<span>{_e(item)}</span>" for item in contact_parts)
    sections_html = "".join(_render_section(b, data, labels) for b in block_order)

    return f"""<!DOCTYPE html>
<html lang="{_e(language)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_e(name)} - Resume</title>
  <style>{_template_css(template_id)}</style>
</head>
<body>
  <header class="cv-header">
    <h1>{_e(name)}</h1>
    {f'<div class="target-role">{_e(data.target_role)}</div>' if data.target_role.strip() else ''}
    <div class="contacts-line">{contacts_html}</div>
  </header>
  <main>
    {sections_html}
  </main>
</body>
</html>"""
