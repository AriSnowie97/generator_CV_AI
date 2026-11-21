"""ATS-friendly HTML templates (minimal, classic, it) without layout tables."""

import html
from typing import Literal

from app.schemas.profile import ProfileData

SECTION_TITLES = {
    "uk": {
        "summary": "Про себе",
        "experience": "Досвід роботи",
        "education": "Освіта",
        "courses": "Курси та сертифікати",
        "skills": "Навички",
        "languages": "Мови",
        "links": "Посилання",
        "present": "дотепер",
        "salary": "Очікування",
        "format": "Формат",
    },
    "en": {
        "summary": "Summary",
        "experience": "Experience",
        "education": "Education",
        "courses": "Courses & Certifications",
        "skills": "Skills",
        "languages": "Languages",
        "links": "Links",
        "present": "Present",
        "salary": "Desired salary",
        "format": "Format",
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


def _render_section(
    block_key: str,
    data: ProfileData,
    labels: dict[str, str],
    template_id: Literal["minimal", "classic", "it"],
) -> str:
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
            company_part = f" <span class='company-sep'>|</span> <span class='company-name'>{_e(exp.company)}</span>" if exp.company else ""
            items_html.append(
                f"""
                <article class="cv-item">
                    <div class="cv-item-header">
                        <div class="cv-item-title"><strong>{_e(exp.position)}</strong>{company_part}</div>
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

    if block_key == "courses":
        valid_courses = [c for c in data.courses if c.title.strip() or c.provider.strip()]
        if not valid_courses:
            return ""
        items_html = []
        for c in valid_courses:
            provider_part = f" <span class='company-sep'>|</span> <span class='company-name'>{_e(c.provider)}</span>" if c.provider.strip() else ""
            cert_part = f"<p class='muted link-url'>{_e(c.certificate_url)}</p>" if c.certificate_url.strip() else ""
            items_html.append(
                f"""
                <article class="cv-item">
                    <div class="cv-item-header">
                        <div class="cv-item-title"><strong>{_e(c.title)}</strong>{provider_part}</div>
                        <div class="cv-item-dates">{_e(c.completion_date)}</div>
                    </div>
                    {cert_part}
                </article>
                """
            )
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['courses'])}</h2>
            {''.join(items_html)}
        </section>
        """

    if block_key == "skills":
        hard = [s.strip() for s in data.skills if s.strip()]
        soft = [s.strip() for s in data.soft_skills if s.strip()]
        if not hard and not soft:
            return ""

        def _render_skill_group(items: list[str], is_soft: bool = False) -> str:
            if template_id == "it":
                cls = "skill-tag soft" if is_soft else "skill-tag"
                chips = "".join(
                    f"<span class='{cls}'>{_e(s)}</span>{'' if i == len(items) - 1 else '<span class=\"ats-sep\">, </span>'}"
                    for i, s in enumerate(items)
                )
                return f"<div class='skills-list'>{chips}</div>"
            return f"<span class='skills-plain'>{_e(', '.join(items))}</span>"

        blocks: list[str] = []
        if hard and soft:
            if template_id == "it":
                blocks.append(f"<div class='skill-group'><div class='skill-group-label'>Hard Skills</div>{_render_skill_group(hard, False)}</div>")
                blocks.append(f"<div class='skill-group'><div class='skill-group-label'>Soft Skills</div>{_render_skill_group(soft, True)}</div>")
            else:
                blocks.append(f"<p class='skills-plain'><strong>Hard Skills:</strong> {_e(', '.join(hard))}</p>")
                blocks.append(f"<p class='skills-plain'><strong>Soft Skills:</strong> {_e(', '.join(soft))}</p>")
        elif hard:
            blocks.append(
                _render_skill_group(hard, False)
                if template_id == "it"
                else f"<p class='skills-plain'>{_e(', '.join(hard))}</p>"
            )
        else:
            if template_id == "it":
                blocks.append(f"<div class='skill-group'><div class='skill-group-label'>Soft Skills</div>{_render_skill_group(soft, True)}</div>")
            else:
                blocks.append(f"<p class='skills-plain'><strong>Soft Skills:</strong> {_e(', '.join(soft))}</p>")

        return f"""
        <section class="cv-section">
            <h2>{_e(labels['skills'])}</h2>
            {''.join(blocks)}
        </section>
        """

    if block_key == "languages":
        valid_langs = [l for l in data.languages if l.name.strip()]
        if not valid_langs:
            return ""
        items = " · ".join(
            f"<strong>{_e(l.name)}</strong>{(' — ' + _e(l.level)) if l.level else ''}"
            for l in valid_langs
        )
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['languages'])}</h2>
            <p class="inline-meta">{items}</p>
        </section>
        """

    if block_key == "links":
        valid_links = [lnk for lnk in data.links if lnk.url.strip()]
        if not valid_links:
            return ""
        items = "".join(
            f"<li><strong>{_e(lnk.label or 'Link')}:</strong> <span class='link-url'>{_e(lnk.url)}</span></li>"
            for lnk in valid_links
        )
        return f"""
        <section class="cv-section">
            <h2>{_e(labels['links'])}</h2>
            <ul class="links-list">{items}</ul>
        </section>
        """

    return ""


def _template_css(template_id: Literal["minimal", "classic", "it"]) -> str:
    base = """
    @page { size: A4; margin: 14mm 16mm; }
    * { box-sizing: border-box; }
    html, body {
        margin: 0;
        padding: 0;
        background: #ffffff;
        color: #111827;
        line-height: 1.48;
        font-size: 10.2pt;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    @media screen {
        body {
            padding: 30px 36px;
        }
    }
    @media screen and (max-width: 520px) {
        body {
            padding: 16px 14px;
            font-size: 9.5pt;
        }
        h1 { font-size: 16pt; }
        .cv-photo { width: 60px; height: 60px; }
        .target-role { font-size: 10.5pt; }
        .cv-item-header {
            flex-direction: column;
            gap: 2px;
        }
        .cv-item-dates { font-size: 8.6pt; }
    }
    @media print {
        body {
            padding: 0;
        }
    }
    h1 { margin: 0 0 3px 0; font-size: 20pt; line-height: 1.15; letter-spacing: -0.01em; }
    .cv-header-inner { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
    .cv-header-text { flex: 1 1 auto; min-width: 0; }
    .cv-photo {
        width: 78px;
        height: 78px;
        border-radius: 12px;
        object-fit: cover;
        flex-shrink: 0;
        border: 1.5px solid #e5e7eb;
    }
    .target-role { font-size: 11.5pt; margin: 0 0 7px 0; }
    .contacts-line { font-size: 9.2pt; color: #374151; line-height: 1.5; }
    .contacts-line .sep { color: #9ca3af; margin: 0 6px; }
    .cv-section { margin-top: 14px; page-break-inside: avoid; }
    .cv-section h2 { font-size: 10.5pt; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.06em; }
    .cv-item { margin-bottom: 10px; }
    .cv-item:last-child { margin-bottom: 0; }
    .cv-item-header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
    .cv-item-title { font-size: 10.3pt; }
    .company-sep { color: #9ca3af; font-weight: 400; }
    .company-name { font-weight: 500; color: #374151; }
    .cv-item-dates { font-size: 9pt; color: #4b5563; white-space: nowrap; }
    ul { margin: 4px 0 0 18px; padding: 0; }
    li { margin-bottom: 3px; }
    p { margin: 2px 0; }
    .summary-text { color: #1f2937; }
    .muted { color: #4b5563; font-size: 9.4pt; }
    .skills-plain { color: #1f2937; line-height: 1.55; }
    .skills-list { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .skill-group { margin-bottom: 7px; }
    .skill-group:last-child { margin-bottom: 0; }
    .skill-group-label { font-size: 8.6pt; font-weight: 700; color: #4b5563; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
    .ats-sep { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
    .inline-meta { font-size: 9.6pt; color: #1f2937; }
    .links-list { list-style: none; margin: 0; padding: 0; font-size: 9.4pt; }
    .links-list li { margin-bottom: 2px; word-break: break-all; }
    .link-url { color: #1f2937; }
    .cv-brand {
        margin-top: 18px;
        padding-top: 6px;
        border-top: 1px solid #f1f5f9;
        text-align: right;
        font-size: 7.5pt;
        color: #9ca3af;
        letter-spacing: 0.02em;
    }
    """

    if template_id == "classic":
        return base + """
        body { font-family: Georgia, "Times New Roman", "Liberation Serif", serif; }
        .cv-header { text-align: center; border-bottom: 1.5px solid #111827; padding-bottom: 10px; }
        .cv-header-inner { flex-direction: column; justify-content: center; gap: 10px; }
        .cv-photo { border-radius: 50%; border-color: #cbd5e1; order: -1; }
        .target-role { color: #374151; font-style: italic; }
        .cv-section h2 { border-bottom: 1px solid #9ca3af; padding-bottom: 3px; color: #111827; }
        """

    if template_id == "it":
        return base + """
        body { font-family: "Segoe UI", Arial, "Liberation Sans", "DejaVu Sans", sans-serif; }
        .cv-header { border-left: 3.5px solid #2563eb; padding-left: 14px; padding-bottom: 2px; }
        .cv-photo { border-radius: 50%; border: 2px solid #bfdbfe; }
        h1 { color: #0f172a; }
        .target-role { color: #1d4ed8; font-weight: 600; }
        .cv-section h2 { color: #1d4ed8; border-bottom: 1px solid #dbeafe; padding-bottom: 3px; }
        .skill-tag {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            border-radius: 5px;
            padding: 2px 8px;
            font-size: 8.8pt;
            font-weight: 500;
        }
        .skill-tag.soft {
            background: #f3f4f6;
            border-color: #d1d5db;
            color: #374151;
        }
        .link-url { color: #1d4ed8; }
        """

    # minimal (Harvard ATS Clean — highest parser compatibility)
    return base + """
    body { font-family: "Segoe UI", Arial, "Liberation Sans", "DejaVu Sans", sans-serif; }
    .cv-header { border-bottom: 1.5px solid #18181b; padding-bottom: 9px; }
    .target-role { color: #27272a; font-weight: 600; }
    .cv-section h2 { color: #111827; border-bottom: 1px solid #d4d4d8; padding-bottom: 2px; }
    """


def render_resume_html(
    data: ProfileData,
    template_id: Literal["minimal", "classic", "it"],
    language: Literal["uk", "en"],
    block_order: list[str],
    show_branding: bool = True,
) -> str:
    """Render complete standalone UTF-8 HTML document for PDF export or screen preview."""
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
    contacts_html = '<span class="sep">|</span>'.join(f"<span>{_e(item)}</span>" for item in contact_parts)
    sections_html = "".join(_render_section(b, data, labels, template_id) for b in block_order)
    brand_text = "Створено в ResumeCraft™" if language == "uk" else "Created with ResumeCraft™"
    brand_html = f'<footer class="cv-brand">{brand_text}</footer>' if show_branding else ""
    photo_uri = (data.contacts.photo_url or "").strip()
    photo_html = (
        f'<img class="cv-photo" src="{photo_uri}" alt="{_e(name)}" />'
        if photo_uri.startswith("data:image/")
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="{_e(language)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="generator" content="ResumeCraft" />
  <meta name="author" content="ResumeCraft — Arina Badovska" />
  <title>{_e(name)} - ResumeCraft</title>
  <style>{_template_css(template_id)}</style>
</head>
<body>
  <header class="cv-header">
    <div class="cv-header-inner">
      <div class="cv-header-text">
        <h1>{_e(name)}</h1>
        {f'<div class="target-role">{_e(data.target_role)}</div>' if data.target_role.strip() else ''}
        <div class="contacts-line">{contacts_html}</div>
      </div>
      {photo_html}
    </div>
  </header>
  <main>
    {sections_html}
  </main>
  {brand_html}
</body>
</html>"""
