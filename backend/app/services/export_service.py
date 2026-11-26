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
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm, Pt, RGBColor
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


def _set_paragraph_border(
    paragraph,
    *,
    bottom: tuple[str, int, int] | None = None,
    top: tuple[str, int, int] | None = None,
    left: tuple[str, int, int] | None = None,
) -> None:
    """Attach clean OpenXML paragraph borders: `(color_hex, sz_eighths_pt, space_pt)`."""
    pPr = paragraph._p.get_or_add_pPr()
    existing = pPr.find(qn("w:pBdr"))
    if existing is not None:
        pPr.remove(existing)
    pBdr = OxmlElement("w:pBdr")
    for side, spec in (("top", top), ("bottom", bottom), ("left", left)):
        if not spec:
            continue
        color_hex, sz, space = spec
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), str(space))
        el.set(qn("w:color"), color_hex)
        pBdr.append(el)
    pPr.append(pBdr)


def _set_run_shading(run, fill_hex: str) -> None:
    """Apply subtle background fill to a text run (for IT template skill tags)."""
    rPr = run._r.get_or_add_rPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill_hex}"/>')
    rPr.append(shd)


def _set_font_family(font_or_style, font_name: str) -> None:
    """Set Latin and Cyrillic-safe OpenXML font family attributes."""
    font_or_style.name = font_name
    rPr = font_or_style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)


def _clear_table_borders(table) -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        "</w:tblBorders>"
    )
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    tblPr.append(borders)


def _style_header_cell(
    cell,
    *,
    width_mm: float,
    bottom_border: tuple[str, int] | None = None,
    left_border: tuple[str, int] | None = None,
    pad_left_dxa: int = 0,
    pad_right_dxa: int = 0,
    pad_bottom_dxa: int = 120,
) -> None:
    cell.width = Mm(width_mm)
    tcPr = cell._tc.get_or_add_tcPr()

    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    tcPr.append(vAlign)

    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="0" w:type="dxa"/>'
        f'<w:left w:w="{pad_left_dxa}" w:type="dxa"/>'
        f'<w:bottom w:w="{pad_bottom_dxa}" w:type="dxa"/>'
        f'<w:right w:w="{pad_right_dxa}" w:type="dxa"/>'
        "</w:tcMar>"
    )
    tcPr.append(tcMar)

    if bottom_border or left_border:
        b_xml = (
            f'<w:bottom w:val="single" w:sz="{bottom_border[1]}" w:space="0" w:color="{bottom_border[0]}"/>'
            if bottom_border
            else '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        )
        l_xml = (
            f'<w:left w:val="single" w:sz="{left_border[1]}" w:space="0" w:color="{left_border[0]}"/>'
            if left_border
            else '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        )
        tcBorders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f"{l_xml}{b_xml}"
            '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            "</w:tcBorders>"
        )
        tcPr.append(tcBorders)


def _prepare_styled_photo_png(
    photo_uri: str, template_id: Literal["minimal", "classic", "it"]
) -> bytes | None:
    """Decode base64 photo and apply template-matching mask (circle or rounded square) + border."""
    if not (photo_uri.startswith("data:image/") and ";base64," in photo_uri):
        return None
    try:
        raw_img = base64.b64decode(photo_uri.split(";base64,", 1)[1])
    except Exception:
        return None

    try:
        from PIL import Image, ImageDraw, ImageOps

        size = 260
        with Image.open(io.BytesIO(raw_img)) as src:
            img = ImageOps.fit(src.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        if template_id in ("classic", "it"):
            draw_mask.ellipse((0, 0, size - 1, size - 1), fill=255)
        else:
            draw_mask.rounded_rectangle((0, 0, size - 1, size - 1), radius=38, fill=255)

        out_img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        out_img.paste(img, (0, 0), mask)

        draw_border = ImageDraw.Draw(out_img)
        if template_id == "it":
            draw_border.ellipse((2, 2, size - 3, size - 3), outline=(0xBF, 0xDB, 0xFE, 255), width=6)
        elif template_id == "classic":
            draw_border.ellipse((2, 2, size - 3, size - 3), outline=(0xCB, 0xD5, 0xE1, 255), width=4)
        else:
            draw_border.rounded_rectangle((2, 2, size - 3, size - 3), radius=38, outline=(0xE5, 0xE7, 0xEB, 255), width=4)

        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return raw_img


def generate_docx_bytes(
    data: ProfileData,
    template_id: Literal["minimal", "classic", "it"],
    language: Literal["uk", "en"],
    block_order: list[str],
    show_branding: bool = True,
) -> bytes:
    """Build an A4 DOCX matching the selected PDF template (minimal, classic, or it)."""
    labels = SECTION_TITLES.get(language, SECTION_TITLES["uk"])
    doc = Document()
    doc.core_properties.author = "ResumeCraft"
    doc.core_properties.comments = "Created with ResumeCraft"

    # Match PDF @page { size: A4; margin: 14mm 16mm; } -> 178mm printable width
    content_width_mm = 178.0
    for section in doc.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(14)
        section.bottom_margin = Mm(14)
        section.left_margin = Mm(16)
        section.right_margin = Mm(16)

    font_name = "Georgia" if template_id == "classic" else "Calibri"
    normal_style = doc.styles["Normal"]
    _set_font_family(normal_style.font, font_name)
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after = Pt(2)
    normal_style.paragraph_format.line_spacing = 1.24

    # Palette matching html_templates.py
    if template_id == "it":
        name_rgb = RGBColor(0x0F, 0x17, 0x2A)
        role_rgb = RGBColor(0x1D, 0x4E, 0xD8)
        heading_rgb = RGBColor(0x1D, 0x4E, 0xD8)
        heading_border_hex = "DBEAFE"
        link_rgb = RGBColor(0x1D, 0x4E, 0xD8)
    elif template_id == "classic":
        name_rgb = RGBColor(0x11, 0x18, 0x27)
        role_rgb = RGBColor(0x37, 0x41, 0x51)
        heading_rgb = RGBColor(0x11, 0x18, 0x27)
        heading_border_hex = "9CA3AF"
        link_rgb = RGBColor(0x1F, 0x29, 0x37)
    else:  # minimal
        name_rgb = RGBColor(0x11, 0x18, 0x27)
        role_rgb = RGBColor(0x27, 0x27, 0x2A)
        heading_rgb = RGBColor(0x11, 0x18, 0x27)
        heading_border_hex = "D4D4D8"
        link_rgb = RGBColor(0x1F, 0x29, 0x37)

    muted_rgb = RGBColor(0x4B, 0x55, 0x63)
    sep_rgb = RGBColor(0x9C, 0xA3, 0xAF)
    body_rgb = RGBColor(0x1F, 0x29, 0x37)

    photo_uri = (data.contacts.photo_url or "").strip() if data.contacts.show_photo else ""
    photo_png = _prepare_styled_photo_png(photo_uri, template_id)

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

    def _fill_header_paragraphs(container, *, align=WD_ALIGN_PARAGRAPH.LEFT, left_bar: bool = False):
        paragraphs = []

        # Name
        p_name = container.paragraphs[0] if (hasattr(container, "paragraphs") and len(container.paragraphs) == 1 and not container.paragraphs[0].text) else container.add_paragraph()
        p_name.alignment = align
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(2)
        p_name.paragraph_format.line_spacing = 1.12
        r_name = p_name.add_run(_display_name(data))
        r_name.bold = True
        r_name.font.size = Pt(20)
        r_name.font.color.rgb = name_rgb
        paragraphs.append(p_name)

        # Target role
        if data.target_role.strip():
            p_role = container.add_paragraph()
            p_role.alignment = align
            p_role.paragraph_format.space_before = Pt(0)
            p_role.paragraph_format.space_after = Pt(4)
            r_role = p_role.add_run(data.target_role.strip())
            r_role.font.size = Pt(11.5)
            r_role.font.color.rgb = role_rgb
            if template_id == "classic":
                r_role.italic = True
            else:
                r_role.bold = True
            paragraphs.append(p_role)

        # Contacts line with muted separators
        if contact_parts:
            p_contacts = container.add_paragraph()
            p_contacts.alignment = align
            p_contacts.paragraph_format.space_before = Pt(0)
            p_contacts.paragraph_format.space_after = Pt(2)
            p_contacts.paragraph_format.line_spacing = 1.25
            for idx, item in enumerate(contact_parts):
                if idx > 0:
                    r_sep = p_contacts.add_run("  |  ")
                    r_sep.font.size = Pt(9)
                    r_sep.font.color.rgb = sep_rgb
                r_item = p_contacts.add_run(item)
                r_item.font.size = Pt(9.2)
                r_item.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
            paragraphs.append(p_contacts)

        if left_bar:
            for p in paragraphs:
                p.paragraph_format.left_indent = Mm(3.5)
                _set_paragraph_border(p, left=("2563EB", 24, 8))

        return paragraphs

    # Render Header matching template_id
    if template_id == "classic":
        if photo_png:
            p_pic = doc.add_paragraph()
            p_pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_pic.paragraph_format.space_before = Pt(0)
            p_pic.paragraph_format.space_after = Pt(6)
            p_pic.add_run().add_picture(io.BytesIO(photo_png), width=Mm(21))
        hdr_ps = _fill_header_paragraphs(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
        if hdr_ps:
            hdr_ps[-1].paragraph_format.space_after = Pt(6)
            _set_paragraph_border(hdr_ps[-1], bottom=("111827", 12, 6))
    elif photo_png:
        # Side-by-side borderless header matching minimal / it CSS flex header
        tbl = doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        _clear_table_borders(tbl)

        left_cell, right_cell = tbl.rows[0].cells
        if template_id == "it":
            _style_header_cell(left_cell, width_mm=150.0, left_border=("2563EB", 24), pad_left_dxa=180, pad_right_dxa=120, pad_bottom_dxa=40)
            _style_header_cell(right_cell, width_mm=28.0, pad_left_dxa=60, pad_right_dxa=0, pad_bottom_dxa=40)
        else:
            _style_header_cell(left_cell, width_mm=150.0, bottom_border=("18181B", 12), pad_left_dxa=0, pad_right_dxa=120, pad_bottom_dxa=120)
            _style_header_cell(right_cell, width_mm=28.0, bottom_border=("18181B", 12), pad_left_dxa=60, pad_right_dxa=0, pad_bottom_dxa=120)

        _fill_header_paragraphs(left_cell, align=WD_ALIGN_PARAGRAPH.LEFT)
        p_pic = right_cell.paragraphs[0]
        p_pic.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_pic.paragraph_format.space_before = Pt(0)
        p_pic.paragraph_format.space_after = Pt(0)
        p_pic.add_run().add_picture(io.BytesIO(photo_png), width=Mm(21))
    else:
        hdr_ps = _fill_header_paragraphs(doc, align=WD_ALIGN_PARAGRAPH.LEFT, left_bar=(template_id == "it"))
        if template_id == "minimal" and hdr_ps:
            hdr_ps[-1].paragraph_format.space_after = Pt(6)
            _set_paragraph_border(hdr_ps[-1], bottom=("18181B", 12, 6))

    def _add_heading(text: str) -> None:
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(11)
        h.paragraph_format.space_after = Pt(5)
        h.paragraph_format.keep_with_next = True
        _set_paragraph_border(h, bottom=(heading_border_hex, 6, 3))
        r = h.add_run(text.upper())
        r.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = heading_rgb

    def _add_item_header(primary: str, secondary: str, dates: str, *, space_after_pt: float = 2.0):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(space_after_pt)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.tab_stops.add_tab_stop(Mm(content_width_mm), WD_TAB_ALIGNMENT.RIGHT)

        r1 = p.add_run(primary)
        r1.bold = True
        r1.font.size = Pt(10.2)
        r1.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

        if secondary:
            r_sep = p.add_run("  |  ")
            r_sep.font.size = Pt(10)
            r_sep.font.color.rgb = sep_rgb
            r2 = p.add_run(secondary)
            r2.font.size = Pt(10)
            r2.font.color.rgb = RGBColor(0x37, 0x41, 0x51)

        if dates:
            r_d = p.add_run(f"\t{dates}")
            r_d.font.size = Pt(9)
            r_d.font.color.rgb = muted_rgb
        return p

    def _add_skill_tags(items: list[str], *, is_soft: bool = False) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        fill = "F3F4F6" if is_soft else "EFF6FF"
        text_rgb = RGBColor(0x37, 0x41, 0x51) if is_soft else RGBColor(0x1E, 0x3A, 0x8A)
        for idx, skill in enumerate(items):
            if idx > 0:
                sp = p.add_run("  ")
                sp.font.size = Pt(9)
            tag = p.add_run(f" {skill} ")
            tag.font.size = Pt(9)
            tag.font.color.rgb = text_rgb
            _set_run_shading(tag, fill)

    for block in block_order:
        if block == "summary" and data.summary.strip():
            _add_heading(labels["summary"])
            p_sum = doc.add_paragraph()
            p_sum.paragraph_format.space_after = Pt(3)
            r_sum = p_sum.add_run(data.summary.strip())
            r_sum.font.color.rgb = body_rgb

        elif block == "experience" and data.experiences:
            _add_heading(labels["experience"])
            for exp in data.experiences:
                dates = _format_dates(exp.start_date, exp.end_date, exp.is_current, labels["present"])
                valid_bullets = [b.strip() for b in exp.bullets if b.strip()]
                head = _add_item_header(
                    exp.position.strip(),
                    exp.company.strip(),
                    dates,
                    space_after_pt=2.0 if valid_bullets else 5.0,
                )
                if not valid_bullets:
                    head.paragraph_format.keep_with_next = False
                for b_idx, bullet in enumerate(valid_bullets):
                    bp = doc.add_paragraph(style="List Bullet")
                    bp.paragraph_format.space_before = Pt(1)
                    bp.paragraph_format.space_after = Pt(5 if b_idx == len(valid_bullets) - 1 else 2)
                    bp.paragraph_format.line_spacing = 1.22
                    br = bp.add_run(bullet)
                    br.font.size = Pt(9.8)
                    br.font.color.rgb = body_rgb

        elif block == "education" and data.education:
            _add_heading(labels["education"])
            for edu in data.education:
                dates = _format_dates(edu.start_date, edu.end_date, edu.is_current, labels["present"])
                details = " — ".join(x.strip() for x in (edu.degree, edu.field_of_study) if x and x.strip())
                head = _add_item_header(
                    edu.institution.strip(),
                    "",
                    dates,
                    space_after_pt=1.0 if details else 5.0,
                )
                if details:
                    p_det = doc.add_paragraph()
                    p_det.paragraph_format.space_before = Pt(0)
                    p_det.paragraph_format.space_after = Pt(5)
                    r_det = p_det.add_run(details)
                    r_det.font.size = Pt(9.4)
                    r_det.font.color.rgb = muted_rgb
                else:
                    head.paragraph_format.keep_with_next = False

        elif block == "courses" and data.courses:
            valid_courses = [c for c in data.courses if c.title.strip() or c.provider.strip()]
            if valid_courses:
                _add_heading(labels["courses"])
                for c in valid_courses:
                    cert_url = c.certificate_url.strip()
                    head = _add_item_header(
                        c.title.strip(),
                        c.provider.strip(),
                        c.completion_date.strip(),
                        space_after_pt=1.0 if cert_url else 5.0,
                    )
                    if cert_url:
                        p_url = doc.add_paragraph()
                        p_url.paragraph_format.space_before = Pt(0)
                        p_url.paragraph_format.space_after = Pt(5)
                        r_url = p_url.add_run(cert_url)
                        r_url.font.size = Pt(9)
                        r_url.font.color.rgb = link_rgb
                    else:
                        head.paragraph_format.keep_with_next = False

        elif block == "skills" and (data.skills or data.soft_skills):
            hard = [s.strip() for s in data.skills if s.strip()]
            soft = [s.strip() for s in data.soft_skills if s.strip()]
            if hard or soft:
                _add_heading(labels["skills"])
                if template_id == "it":
                    if hard and soft:
                        lbl1 = doc.add_paragraph()
                        lbl1.paragraph_format.space_after = Pt(1)
                        lbl1.paragraph_format.keep_with_next = True
                        rl1 = lbl1.add_run("HARD SKILLS")
                        rl1.bold = True
                        rl1.font.size = Pt(8.5)
                        rl1.font.color.rgb = muted_rgb
                        _add_skill_tags(hard, is_soft=False)

                        lbl2 = doc.add_paragraph()
                        lbl2.paragraph_format.space_before = Pt(3)
                        lbl2.paragraph_format.space_after = Pt(1)
                        lbl2.paragraph_format.keep_with_next = True
                        rl2 = lbl2.add_run("SOFT SKILLS")
                        rl2.bold = True
                        rl2.font.size = Pt(8.5)
                        rl2.font.color.rgb = muted_rgb
                        _add_skill_tags(soft, is_soft=True)
                    elif hard:
                        _add_skill_tags(hard, is_soft=False)
                    else:
                        lbl2 = doc.add_paragraph()
                        lbl2.paragraph_format.space_after = Pt(1)
                        lbl2.paragraph_format.keep_with_next = True
                        rl2 = lbl2.add_run("SOFT SKILLS")
                        rl2.bold = True
                        rl2.font.size = Pt(8.5)
                        rl2.font.color.rgb = muted_rgb
                        _add_skill_tags(soft, is_soft=True)
                else:
                    if hard and soft:
                        p1 = doc.add_paragraph()
                        p1.paragraph_format.space_after = Pt(3)
                        r_h = p1.add_run("Hard Skills: ")
                        r_h.bold = True
                        p1.add_run(", ".join(hard)).font.color.rgb = body_rgb

                        p2 = doc.add_paragraph()
                        p2.paragraph_format.space_after = Pt(3)
                        r_s = p2.add_run("Soft Skills: ")
                        r_s.bold = True
                        p2.add_run(", ".join(soft)).font.color.rgb = body_rgb
                    elif hard:
                        p1 = doc.add_paragraph()
                        p1.paragraph_format.space_after = Pt(3)
                        p1.add_run(", ".join(hard)).font.color.rgb = body_rgb
                    else:
                        p2 = doc.add_paragraph()
                        p2.paragraph_format.space_after = Pt(3)
                        r_s = p2.add_run("Soft Skills: ")
                        r_s.bold = True
                        p2.add_run(", ".join(soft)).font.color.rgb = body_rgb

        elif block == "languages" and data.languages:
            valid_langs = [l for l in data.languages if l.name.strip()]
            if valid_langs:
                _add_heading(labels["languages"])
                p_lang = doc.add_paragraph()
                p_lang.paragraph_format.space_after = Pt(3)
                for idx, lang in enumerate(valid_langs):
                    if idx > 0:
                        rs = p_lang.add_run("  ·  ")
                        rs.font.color.rgb = sep_rgb
                    rn = p_lang.add_run(lang.name.strip())
                    rn.bold = True
                    rn.font.size = Pt(9.6)
                    if lang.level.strip():
                        rl = p_lang.add_run(f" — {lang.level.strip()}")
                        rl.font.size = Pt(9.6)
                        rl.font.color.rgb = body_rgb

        elif block == "links" and data.links:
            valid_links = [l for l in data.links if l.url.strip()]
            if valid_links:
                _add_heading(labels["links"])
                for lnk in valid_links:
                    p_lnk = doc.add_paragraph()
                    p_lnk.paragraph_format.space_after = Pt(2)
                    rl = p_lnk.add_run(f"{(lnk.label or 'Link').strip()}: ")
                    rl.bold = True
                    rl.font.size = Pt(9.4)
                    ru = p_lnk.add_run(lnk.url.strip())
                    ru.font.size = Pt(9.4)
                    ru.font.color.rgb = link_rgb

    if show_branding:
        brand_p = doc.add_paragraph()
        brand_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        brand_p.paragraph_format.space_before = Pt(14)
        brand_p.paragraph_format.space_after = Pt(0)
        _set_paragraph_border(brand_p, top=("F1F5F9", 4, 4))
        brand_run = brand_p.add_run("Створено в ResumeCraft™" if language == "uk" else "Created with ResumeCraft™")
        brand_run.font.size = Pt(7.5)
        brand_run.font.color.rgb = sep_rgb

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
