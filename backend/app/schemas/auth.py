"""Authentication and account schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    consent_accepted: bool

    @field_validator("consent_accepted")
    @classmethod
    def must_accept_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Необхідно надати згоду на обробку персональних даних")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    code: Optional[str] = None
    consent_accepted: bool = True


class VerifyEmailRequest(BaseModel):
    token: Optional[str] = Field(default=None, min_length=8, max_length=256)
    code: Optional[str] = Field(default=None, min_length=6, max_length=6)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: str
    email: str
    is_email_verified: bool
    consent_accepted: bool
    preferred_interface_language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    verification_token_preview: Optional[str] = None
    email_sent: bool = False
    email_delivery_mode: str = "dev"


class ResendVerificationResponse(BaseModel):
    email_sent: bool
    email_delivery_mode: str
    message: str
    verification_token_preview: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    preferred_interface_language: str = Field(pattern="^(uk|en)$")
