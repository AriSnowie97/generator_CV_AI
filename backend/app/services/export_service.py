"""PDF (Headless Chromium) and DOCX resume export service."""

import base64
import io
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Literal

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.storage import file_storage
from app.models.models import EventLog, ExportFile, User
from app.schemas.ai import AIFilenameRequest
from app.schemas.profile import ProfileData
from app.services.ai_service import generate_resume_filename
from app.services.html_templates import SECTION_TITLES, _display_name, _format_dates, render_resume_html


def _find_chromium_binary() -> str | None:
    """Locate Chrome/Chromium/Edge executable for headless PDF generation."""
    env_bin = os.getenv("CHROMIUM_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin

    for candidate in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(candidate)
        if found:
            return found

    windows_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path_str in windows_paths:
        if Path(path_str).exists():
            return path_str
    return None


def generate_pdf_bytes(html_content: str) -> bytes:
    """Render HTML into a selectable-text PDF with UTF-8 Cyrillic support via Headless Chromium."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_file = tmp_path / "resume.html"
        pdf_file = tmp_path / "resume.pdf"
        html_file.write_text(html_content, encoding="utf-8")

        # Try Playwright first (preferred inside Docker Linux container)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                page = browser.new_page()
                page.goto(html_file.as_uri(), wait_until="load")
                page.pdf(path=str(pdf_file), format="A4", print_background=True)
                browser.close()
            if pdf_file.exists() and pdf_file.stat().st_size > 0:
                return pdf_file.read_bytes()
        except Exception:
            pass

        # Fallback to installed Chromium / Chrome / Edge binary
        chromium_bin = _find_chromium_binary()
        if not chromium_bin:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не знайдено Headless Chromium/Chrome для генерації PDF",
            )

        user_data_dir = tmp_path / "chrome_profile"
        cmd = [
            chromium_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={user_data_dir}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_file}",
            html_file.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if not pdf_file.exists() or pdf_file.stat().st_size == 0:
            # Older Chromium versions use --headless instead of --headless=new
            cmd[1] = "--headless"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)

        if not pdf_file.exists() or pdf_file.stat().st_size == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Помилка генерації PDF: {result.stderr[:200]}",
            )
        return pdf_file.read_bytes()


def generate_docx_bytes(
    data: ProfileData,
    template_id: Literal["minimal", "classic", "it"],
    language: Literal["uk", "en"],
    block_order: list[str],
    show_branding: bool = True,
) -> bytes:
    """Build a clean, watermark-free DOCX document respecting block order and language."""
    labels = SECTION_TITLES.get(language, SECTION_TITLES["uk"])
    doc = Document()
    doc.core_properties.author = "ResumeCraft — Аріна Бадовська"
    doc.core_properties.comments = "Created with ResumeCraft"

    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Georgia" if template_id == "classic" else "Calibri"
    normal_style.font.size = Pt(10.5)

    accent_rgb = RGBColor(0x25, 0x63, 0xEB) if template_id == "it" else RGBColor(0x18, 0x18, 0x1B)

    photo_uri = (data.contacts.photo_url or "").strip()
    if photo_uri.startswith("data:image/") and ";base64," in photo_uri:
        try:
            raw_img = base64.b64decode(photo_uri.split(";base64,", 1)[1])
            pic_p = doc.add_paragraph()
            pic_p.paragraph_format.space_after = Pt(6)
            pic_p.add_run().add_picture(io.BytesIO(raw_img), width=Inches(1.05))
        except Exception:
            pass

    title_p = doc.add_paragraph()
    title_run = title_p.add_run(_display_name(data))
    title_run.bold = True
    title_run.font.size = Pt(20)
    title_run.font.color.rgb = accent_rgb

    if data.target_role.strip():
        role_p = doc.add_paragraph()
        role_run = role_p.add_run(data.target_role.strip())
        role_run.font.size = Pt(12)
        role_run.font.color.rgb = accent_rgb

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
    if contact_parts:
        c_p = doc.add_paragraph(" | ".join(contact_parts))
        c_p.runs[0].font.size = Pt(9.5)
        c_p.runs[0].font.color.rgb = RGBColor(0x52, 0x52, 0x5B)

    def _add_heading(text: str):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        r = h.add_run(text.upper())
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = accent_rgb

    for block in block_order:
        if block == "summary" and data.summary.strip():
            _add_heading(labels["summary"])
            doc.add_paragraph(data.summary.strip())

        elif block == "experience" and data.experiences:
            _add_heading(labels["experience"])
            for exp in data.experiences:
                dates = _format_dates(exp.start_date, exp.end_date, exp.is_current, labels["present"])
                head = doc.add_paragraph()
                head.paragraph_format.space_after = Pt(2)
                r1 = head.add_run(f"{exp.position}{(' · ' + exp.company) if exp.company else ''}")
                r1.bold = True
                if dates:
                    r2 = head.add_run(f"   ({dates})")
                    r2.font.size = Pt(9.5)
                    r2.font.color.rgb = RGBColor(0x52, 0x52, 0x5B)
                for bullet in exp.bullets:
                    if bullet.strip():
                        doc.add_paragraph(bullet.strip(), style="List Bullet")

        elif block == "education" and data.education:
            _add_heading(labels["education"])
            for edu in data.education:
                dates = _format_dates(edu.start_date, edu.end_date, edu.is_current, labels["present"])
                p = doc.add_paragraph()
                r1 = p.add_run(edu.institution)
                r1.bold = True
                details = " — ".join(x for x in (edu.degree, edu.field_of_study) if x)
                if details:
                    p.add_run(f"\n{details}")
                if dates:
                    r_d = p.add_run(f" ({dates})")
                    r_d.font.size = Pt(9.5)
                    r_d.font.color.rgb = RGBColor(0x52, 0x52, 0x5B)

        elif block == "courses" and data.courses:
            valid_courses = [c for c in data.courses if c.title.strip() or c.provider.strip()]
            if valid_courses:
                _add_heading(labels["courses"])
                for c in valid_courses:
                    p = doc.add_paragraph()
                    r1 = p.add_run(c.title.strip())
                    r1.bold = True
                    if c.provider.strip():
                        p.add_run(f" · {c.provider.strip()}")
                    if c.completion_date.strip():
                        r_d = p.add_run(f" ({c.completion_date.strip()})")
                        r_d.font.size = Pt(9.5)
                        r_d.font.color.rgb = RGBColor(0x52, 0x52, 0x5B)
                    if c.certificate_url.strip():
                        p.add_run(f"\n{c.certificate_url.strip()}")

        elif block == "skills" and (data.skills or data.soft_skills):
            hard = [s.strip() for s in data.skills if s.strip()]
            soft = [s.strip() for s in data.soft_skills if s.strip()]
            if hard or soft:
                _add_heading(labels["skills"])
                if hard and soft:
                    p1 = doc.add_paragraph()
                    p1.add_run("Hard Skills: ").bold = True
                    p1.add_run(", ".join(hard))
                    p2 = doc.add_paragraph()
                    p2.add_run("Soft Skills: ").bold = True
                    p2.add_run(", ".join(soft))
                elif hard:
                    doc.add_paragraph(", ".join(hard))
                else:
                    p2 = doc.add_paragraph()
                    p2.add_run("Soft Skills: ").bold = True
                    p2.add_run(", ".join(soft))

        elif block == "languages" and data.languages:
            items = [f"{l.name}{' — ' + l.level if l.level else ''}" for l in data.languages if l.name.strip()]
            if items:
                _add_heading(labels["languages"])
                doc.add_paragraph(" | ".join(items))

        elif block == "links" and data.links:
            items = [f"{l.label or 'Link'}: {l.url}" for l in data.links if l.url.strip()]
            if items:
                _add_heading(labels["links"])
                for item in items:
                    doc.add_paragraph(item)

    if show_branding:
        brand_p = doc.add_paragraph()
        brand_p.paragraph_format.space_before = Pt(14)
        brand_run = brand_p.add_run("Створено в ResumeCraft™" if language == "uk" else "Created with ResumeCraft™")
        brand_run.font.size = Pt(8)
        brand_run.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_resume_file(
    db: Session,
    user: User,
    fmt: Literal["pdf", "docx"],
    template_id: Literal["minimal", "classic", "it"],
    language: Literal["uk", "en"],
    block_order: list[str],
    data: ProfileData,
    use_ai_filename: bool = True,
    show_branding: bool = True,
) -> tuple[bytes, str, str]:
    """Generate PDF or DOCX, persist in storage, log analytics events, and return `(bytes, filename, media_type)`."""
    fname_req = AIFilenameRequest(
        first_name=data.contacts.first_name,
        last_name=data.contacts.last_name,
        full_name=data.contacts.full_name,
        target_role=data.target_role,
        format=fmt,
    )
    filename, _, _ = generate_resume_filename(db, user, fname_req, count_quota=False)

    if fmt == "pdf":
        html_doc = render_resume_html(data, template_id, language, block_order, show_branding=show_branding)
        file_bytes = generate_pdf_bytes(html_doc)
        media_type = "application/pdf"
    else:
        file_bytes = generate_docx_bytes(data, template_id, language, block_order, show_branding=show_branding)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    storage_key = f"exports/{user.id}/{uuid.uuid4()}.{fmt}"
    file_storage.save_bytes(storage_key, file_bytes, media_type)
    db.add(ExportFile(user_id=user.id, format=fmt, filename=filename, storage_key=storage_key))

    if fmt == "pdf":
        has_first_pdf = (
            db.query(EventLog)
            .filter(EventLog.user_id == user.id, EventLog.event_type == "first_pdf_download")
            .first()
            is not None
        )
        if not has_first_pdf:
            db.add(EventLog(user_id=user.id, event_type="first_pdf_download", metadata_json={"template_id": template_id}))

    db.add(EventLog(user_id=user.id, event_type=f"export_{fmt}", metadata_json={"template_id": template_id}))
    db.commit()

    return file_bytes, filename, media_type
