"""Authentication, email verification, Google OAuth, and account deletion services."""

import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, rate_limiter, verify_password
from app.core.storage import file_storage
from app.models.models import EventLog, Profile, Resume, User
from app.schemas.auth import GoogleAuthRequest, LoginRequest, RegisterRequest, VerifyEmailRequest
from app.schemas.profile import ProfileData
from app.services.email_service import DeliveryMode, send_verification_email


def _default_profile_dict(email: str) -> dict:
    data = ProfileData()
    data.contacts.email = email
    return data.model_dump()


def _generate_verification_bundle() -> tuple[str, str, str]:
    """Return (6-digit code, url_token, combined_db_value)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    url_token = secrets.token_urlsafe(24)
    return code, url_token, f"{code}:{url_token}"


def _parse_stored_verification(stored: str | None) -> tuple[str, str]:
    """Split stored `code:url_token` (or legacy plain token)."""
    raw = (stored or "").strip()
    if ":" in raw:
        code, url_token = raw.split(":", 1)
        return code, url_token
    return "", raw


def _build_verify_url(base_url: str, url_token: str) -> str:
    clean_base = (base_url or get_settings().BACKEND_URL or "http://localhost:8000").rstrip("/")
    return f"{clean_base}/?{urlencode({'verify_token': url_token})}"


def register_user(
    db: Session, payload: RegisterRequest, public_base_url: str = ""
) -> tuple[User, str, str | None, bool, DeliveryMode]:
    """Register a new user with email + password, mandatory consent, and real email verification."""
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач із таким email вже зареєстрований",
        )

    code, url_token, stored_bundle = _generate_verification_bundle()
    now = datetime.now(timezone.utc)
    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        is_email_verified=False,
        email_verification_token=stored_bundle,
        consent_accepted=True,
        consent_accepted_at=now,
    )
    db.add(user)
    db.flush()

    default_data = _default_profile_dict(normalized_email)
    profile = Profile(user_id=user.id, data_json=default_data, completeness_score=10)
    resume = Resume(user_id=user.id, title="Моє резюме", template_id="minimal", language="uk", data_json=default_data)
    event = EventLog(user_id=user.id, event_type="register", metadata_json={"method": "email"})
    db.add_all([profile, resume, event])
    db.commit()
    db.refresh(user)

    verify_url = _build_verify_url(public_base_url, url_token)
    email_sent, delivery_mode = send_verification_email(normalized_email, code, verify_url)
    preview_token = url_token if delivery_mode == "dev" else None

    token = create_access_token(user.id)
    return user, token, preview_token, email_sent, delivery_mode


def login_user(db: Session, payload: LoginRequest, client_ip: str) -> tuple[User, str]:
    """Authenticate user by email + password with rate limiting."""
    settings = get_settings()
    normalized_email = payload.email.strip().lower()
    rate_key = f"login:{client_ip}:{normalized_email}"

    allowed, retry_after = rate_limiter.check_and_record(
        rate_key,
        settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Забагато невдалих спроб входу. Спробуйте через {retry_after} с.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
        )

    rate_limiter.reset(rate_key)
    db.add(EventLog(user_id=user.id, event_type="login", metadata_json={"method": "email"}))
    db.commit()
    token = create_access_token(user.id)
    return user, token


def verify_user_email(
    db: Session,
    payload: VerifyEmailRequest,
    client_ip: str = "unknown",
    current_user: User | None = None,
) -> User:
    """Confirm user's email address via magic link token OR 6-digit code."""
    if payload.token:
        clean_tok = payload.token.strip()
        # Match either full stored value or `<code>:<url_token>` suffix
        user = (
            db.query(User)
            .filter(
                (User.email_verification_token == clean_tok)
                | (User.email_verification_token.like(f"%:{clean_tok}"))
            )
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недійсне або застаріле посилання підтвердження email",
            )
        stored_code, stored_tok = _parse_stored_verification(user.email_verification_token)
        if not (secrets.compare_digest(stored_tok, clean_tok) or secrets.compare_digest(user.email_verification_token or "", clean_tok)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недійсне або застаріле посилання підтвердження email",
            )
    elif payload.code:
        clean_code = payload.code.strip()
        target_email = (payload.email or (current_user.email if current_user else "") or "").strip().lower()
        if not target_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вкажіть email для підтвердження кодом",
            )
        rate_key = f"verify_code:{client_ip}:{target_email}"
        allowed, retry_after = rate_limiter.check_and_record(rate_key, max_attempts=6, window_seconds=600)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Забагато спроб введення коду. Спробуйте через {retry_after} с.",
            )
        user = db.query(User).filter(User.email == target_email).first()
        if not user or not user.email_verification_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невірний код або email уже підтверджено",
            )
        stored_code, _ = _parse_stored_verification(user.email_verification_token)
        if not stored_code or not secrets.compare_digest(stored_code, clean_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невірний 6-значний код підтвердження",
            )
        rate_limiter.reset(rate_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Передайте токен із листа або 6-значний код підтвердження",
        )

    user.is_email_verified = True
    user.email_verification_token = None
    db.commit()
    db.refresh(user)
    return user


def resend_verification_email(
    db: Session, user: User, public_base_url: str = ""
) -> tuple[bool, DeliveryMode, str | None]:
    """Generate a fresh code+link and resend verification email (rate-limited to 1 per 60s)."""
    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вашу електронну пошту вже підтверджено",
        )

    rate_key = f"resend_verify:{user.id}"
    allowed, retry_after = rate_limiter.check_and_record(rate_key, max_attempts=1, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Повторний лист можна надіслати через {retry_after} с.",
        )

    code, url_token, stored_bundle = _generate_verification_bundle()
    user.email_verification_token = stored_bundle
    db.commit()

    verify_url = _build_verify_url(public_base_url, url_token)
    email_sent, delivery_mode = send_verification_email(user.email, code, verify_url)
    preview_token = url_token if delivery_mode == "dev" else None
    return email_sent, delivery_mode, preview_token


async def google_oauth_login(db: Session, payload: GoogleAuthRequest) -> tuple[User, str]:
    """Sign in or register using a Google ID token or authorization code."""
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth ще не налаштований на сервері (відсутній GOOGLE_CLIENT_ID). Використайте вхід через email.",
        )

    id_token = payload.id_token
    if not id_token and payload.code:
        if not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Відсутній GOOGLE_CLIENT_SECRET для обміну коду авторизації.",
            )
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": payload.code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": f"{settings.FRONTEND_URL}/login",
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Помилка авторизації через Google")
            id_token = token_resp.json().get("id_token")

    if not id_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не передано Google token")

    async with httpx.AsyncClient(timeout=10.0) as client:
        info_resp = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token})
    if info_resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недійсний Google токен")

    info = info_resp.json()
    if info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google токен належить іншому застосунку")

    email = str(info.get("email", "")).strip().lower()
    google_sub = str(info.get("sub", "")).strip()
    if not email or not google_sub:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google не надав email акаунта")

    user = db.query(User).filter((User.google_id == google_sub) | (User.email == email)).first()
    if not user:
        if not payload.consent_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необхідно надати згоду на обробку персональних даних",
            )
        user = User(
            email=email,
            google_id=google_sub,
            is_email_verified=True,
            consent_accepted=True,
            consent_accepted_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()
        default_data = _default_profile_dict(email)
        db.add(Profile(user_id=user.id, data_json=default_data, completeness_score=10))
        db.add(Resume(user_id=user.id, title="Моє резюме", template_id="minimal", language="uk", data_json=default_data))
        db.add(EventLog(user_id=user.id, event_type="register", metadata_json={"method": "google"}))
    else:
        if not user.google_id:
            user.google_id = google_sub
        user.is_email_verified = True
        db.add(EventLog(user_id=user.id, event_type="login", metadata_json={"method": "google"}))

    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id)


def delete_user_account(db: Session, user: User) -> None:
    """Completely erase user account, profile, resume, logs, and exported files."""
    file_storage.delete_prefix(f"exports/{user.id}/")
    db.delete(user)
    db.commit()
