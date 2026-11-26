"""Transactional email delivery service (Brevo API, Resend API, or SMTP) for email verification."""

import html
import logging
import smtplib
from email.message import EmailMessage
from typing import Literal

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DeliveryMode = Literal["sent", "dev", "failed"]


def active_email_provider() -> Literal["brevo", "resend", "smtp", "none"]:
    """Detect which real email provider is configured via environment variables."""
    settings = get_settings()
    if settings.BREVO_API_KEY and settings.BREVO_API_KEY.strip():
        return "brevo"
    if settings.RESEND_API_KEY and settings.RESEND_API_KEY.strip():
        return "resend"
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        return "smtp"
    return "none"


def is_real_email_configured() -> bool:
    return active_email_provider() != "none"


def _resolve_sender() -> tuple[str, str]:
    settings = get_settings()
    sender_email = (settings.EMAIL_FROM or settings.SMTP_USER or "noreply@resumecraft.app").strip()
    sender_name = (settings.EMAIL_FROM_NAME or "ResumeCraft").strip()
    return sender_name, sender_email


def build_verification_email(to_email: str, code: str, verify_url: str) -> tuple[str, str, str]:
    """Return (subject, plain_text, html_body) for email verification."""
    subject = f"ResumeCraft — код підтвердження пошти: {code}"
    safe_url = html.escape(verify_url, quote=True)
    safe_code = html.escape(code)
    safe_email = html.escape(to_email)

    plain = (
        f"Вітаємо у ResumeCraft!\n\n"
        f"Ваш 6-значний код підтвердження електронної пошти ({to_email}): {code}\n\n"
        f"Або підтвердіть пошту в один клік за посиланням:\n{verify_url}\n\n"
        f"Якщо ви не реєструвалися в ResumeCraft, просто проігноруйте цей лист.\n"
        f"— Команда ResumeCraft™"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="UTF-8" /></head>
<body style="margin:0; padding:0; background:#f8fafc; font-family:'Segoe UI',Arial,sans-serif; color:#0f172a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:28px 14px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px; background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:28px;">
          <tr>
            <td style="padding-bottom:16px; border-bottom:1px solid #e2e8f0;">
              <strong style="font-size:19px; color:#2563eb;">ResumeCraft™</strong>
              <span style="font-size:12px; color:#64748b; margin-left:8px;">ATS-генератор резюме</span>
            </td>
          </tr>
          <tr>
            <td style="padding-top:20px;">
              <h2 style="margin:0 0 10px; font-size:20px; color:#0f172a;">Підтвердіть вашу електронну пошту</h2>
              <p style="margin:0 0 18px; font-size:14.5px; line-height:1.55; color:#334155;">
                Ви зареєстрували акаунт у <strong>ResumeCraft</strong> для адреси <strong>{safe_email}</strong>.
                Введіть цей код у формі підтвердження на сайті:
              </p>
              <div style="text-align:center; margin:18px 0 22px;">
                <span style="display:inline-block; padding:14px 28px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:12px; font-size:30px; font-weight:800; letter-spacing:8px; color:#1d4ed8;">
                  {safe_code}
                </span>
              </div>
              <p style="margin:0 0 16px; font-size:14px; color:#334155; text-align:center;">
                Або підтвердіть пошту в один клік:
              </p>
              <div style="text-align:center; margin-bottom:22px;">
                <a href="{safe_url}" style="display:inline-block; padding:12px 26px; background:#2563eb; color:#ffffff; text-decoration:none; border-radius:10px; font-weight:700; font-size:14.5px;">
                  Підтвердити email
                </a>
              </div>
              <p style="margin:0; font-size:12px; line-height:1.5; color:#64748b; word-break:break-all;">
                Якщо кнопка не відкривається, скопіюйте посилання у браузер:<br />
                <a href="{safe_url}" style="color:#2563eb;">{safe_url}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding-top:20px; border-top:1px solid #e2e8f0; margin-top:20px; font-size:11.5px; color:#94a3b8;">
              Якщо ви не створювали акаунт у ResumeCraft, просто проігноруйте цей лист.<br />
              © 2026 ResumeCraft™
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return subject, plain, html_body


def send_verification_email(to_email: str, code: str, verify_url: str) -> tuple[bool, DeliveryMode]:
    """Send real verification email via configured provider (Brevo / Resend / SMTP)."""
    provider = active_email_provider()
    if provider == "none":
        logger.info("Email provider not configured; running in dev verification mode for %s", to_email)
        return False, "dev"

    settings = get_settings()
    sender_name, sender_email = _resolve_sender()
    subject, plain_body, html_body = build_verification_email(to_email, code, verify_url)

    try:
        if provider == "brevo":
            resp = httpx.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.BREVO_API_KEY.strip(),
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json={
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "htmlContent": html_body,
                    "textContent": plain_body,
                },
                timeout=12.0,
            )
            if resp.status_code in (200, 201, 202):
                logger.info("Verification email sent via Brevo to %s", to_email)
                return True, "sent"
            logger.error("Brevo email failed (%s): %s", resp.status_code, resp.text[:300])
            return False, "failed"

        if provider == "resend":
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{sender_name} <{sender_email}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": plain_body,
                },
                timeout=12.0,
            )
            if resp.status_code in (200, 201, 202):
                logger.info("Verification email sent via Resend to %s", to_email)
                return True, "sent"
            logger.error("Resend email failed (%s): %s", resp.status_code, resp.text[:300])
            return False, "failed"

        if provider == "smtp":
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = to_email
            msg.set_content(plain_body)
            msg.add_alternative(html_body, subtype="html")

            port = int(settings.SMTP_PORT or 587)
            use_ssl = settings.SMTP_USE_SSL or port == 465
            if use_ssl:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=12) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.SMTP_HOST, port, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            logger.info("Verification email sent via SMTP to %s", to_email)
            return True, "sent"

    except Exception as exc:
        logger.exception("Failed to send verification email via %s: %s", provider, exc)
        return False, "failed"

    return False, "failed"
