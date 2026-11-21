"""Authentication endpoints: register, login, email verification, Google OAuth."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import User
from app.schemas.auth import (
    AuthResponse,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    google_oauth_login,
    login_user,
    register_user,
    resend_verification_email,
    verify_user_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _resolve_public_base_url(request: Request) -> str:
    settings = get_settings()
    if settings.BACKEND_URL and not settings.BACKEND_URL.startswith("http://localhost"):
        return settings.BACKEND_URL.rstrip("/")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    if host:
        return f"{proto}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    user, token, preview_token, email_sent, delivery_mode = register_user(
        db, payload, public_base_url=_resolve_public_base_url(request)
    )
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        verification_token_preview=preview_token,
        email_sent=email_sent,
        email_delivery_mode=delivery_mode,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    user, token = login_user(db, payload, client_ip)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/verify-email", response_model=UserResponse)
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    user = verify_user_email(db, payload, client_ip=client_ip)
    return UserResponse.model_validate(user)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_sent, delivery_mode, preview_token = resend_verification_email(
        db, current_user, public_base_url=_resolve_public_base_url(request)
    )
    if delivery_mode == "sent":
        msg = f"Лист із новим кодом та посиланням надіслано на {current_user.email}. Перевірте також папку «Спам»."
    elif delivery_mode == "dev":
        msg = "Поштовий провайдер ще не підключений (dev-режим). Використайте кнопку тестового підтвердження."
    else:
        msg = "Не вдалося надіслати лист через поштовий сервер. Перевірте налаштування SMTP/API."
    return ResendVerificationResponse(
        email_sent=email_sent,
        email_delivery_mode=delivery_mode,
        message=msg,
        verification_token_preview=preview_token,
    )


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    user, token = await google_oauth_login(db, payload)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
