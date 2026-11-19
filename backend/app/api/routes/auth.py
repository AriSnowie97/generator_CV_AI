"""Authentication endpoints: register, login, email verification, Google OAuth."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.auth import (
    AuthResponse,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    google_oauth_login,
    login_user,
    register_user,
    verify_user_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user, token, verify_token = register_user(db, payload)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        verification_token_preview=verify_token,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    user, token = login_user(db, payload, client_ip)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/verify-email", response_model=UserResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = verify_user_email(db, payload.token)
    return UserResponse.model_validate(user)


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    user, token = await google_oauth_login(db, payload)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
