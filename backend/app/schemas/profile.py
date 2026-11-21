"""Profile and resume content schemas with ТЗ validation rules."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-\d{2})?$")
SAFE_PHOTO_DATA_URI_RE = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=]+$")


def _parse_sortable_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    val = value.strip()
    if not val:
        return None
    # Accept MM.YYYY or MM/YYYY and normalize to YYYY-MM
    m_dmy = re.match(r"^(0[1-9]|1[0-2])[./](\d{4})$", val)
    if m_dmy:
        return f"{m_dmy.group(2)}-{m_dmy.group(1)}"
    # Accept plain YYYY
    if re.match(r"^\d{4}$", val):
        return f"{val}-01"
    if not DATE_RE.match(val):
        raise ValueError("Формат дати має бути РРРР-ММ (оберіть місяць і рік зі списку)")
    return val[:7]


class ContactInfo(BaseModel):
    full_name: str = Field(default="", max_length=120)
    first_name: str = Field(default="", max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: Optional[EmailStr | str] = ""
    phone: str = Field(default="", max_length=30)
    location: str = Field(default="", max_length=120)
    photo_url: str = Field(default="", max_length=700_000)

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, v: str) -> str:
        val = (v or "").strip()
        if not val:
            return ""
        if not SAFE_PHOTO_DATA_URI_RE.match(val):
            raise ValueError("Недопустимий формат фото (дозволені лише JPG, PNG або WebP)")
        return val

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            return ""
        val = str(v).strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val):
            raise ValueError("Некоректний формат email")
        return val

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        val = (v or "").strip()
        if not val:
            return ""
        digits = re.sub(r"\D", "", val)
        if not PHONE_RE.match(val) or len(digits) < 7 or len(digits) > 15:
            raise ValueError("Некоректний формат телефону (приклад: +380501234567)")
        return val


class ExperienceItem(BaseModel):
    id: str = Field(default="")
    company: str = Field(default="", max_length=120)
    position: str = Field(default="", max_length=120)
    start_date: str = Field(default="", max_length=16)
    end_date: str = Field(default="", max_length=16)
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def validate_dates(self) -> "ExperienceItem":
        start = _parse_sortable_date(self.start_date)
        end = None if self.is_current else _parse_sortable_date(self.end_date)
        if start and end and end < start:
            raise ValueError("Дата завершення не може бути раніше дати початку")
        return self


class EducationItem(BaseModel):
    id: str = Field(default="")
    institution: str = Field(default="", max_length=150)
    degree: str = Field(default="", max_length=120)
    field_of_study: str = Field(default="", max_length=120)
    start_date: str = Field(default="", max_length=16)
    end_date: str = Field(default="", max_length=16)
    is_current: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "EducationItem":
        start = _parse_sortable_date(self.start_date)
        end = None if self.is_current else _parse_sortable_date(self.end_date)
        if start and end and end < start:
            raise ValueError("Дата завершення освіти не може бути раніше дати початку")
        return self


class LanguageItem(BaseModel):
    name: str = Field(default="", max_length=60)
    level: str = Field(default="", max_length=60)


class LinkItem(BaseModel):
    label: str = Field(default="", max_length=60)
    url: str = Field(default="", max_length=300)


class CourseItem(BaseModel):
    id: str = Field(default="")
    title: str = Field(default="", max_length=160)
    provider: str = Field(default="", max_length=120)
    completion_date: str = Field(default="", max_length=16)
    certificate_url: str = Field(default="", max_length=300)


class ProfileData(BaseModel):
    contacts: ContactInfo = Field(default_factory=ContactInfo)
    target_role: str = Field(default="", max_length=120)
    summary: str = Field(default="", max_length=2000)
    desired_salary: str = Field(default="", max_length=60)
    work_format: str = Field(default="", max_length=60)
    experiences: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    courses: list[CourseItem] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
    links: list[LinkItem] = Field(default_factory=list)

    @field_validator("experiences")
    @classmethod
    def check_max_experiences(cls, v: list[ExperienceItem]) -> list[ExperienceItem]:
        if len(v) > 15:
            raise ValueError("Максимум 15 місць роботи")
        return v

    @field_validator("skills")
    @classmethod
    def check_max_skills(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) > 30:
            raise ValueError("Максимум 30 навичок")
        return cleaned

    @field_validator("soft_skills")
    @classmethod
    def check_max_soft_skills(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) > 15:
            raise ValueError("Максимум 15 soft skills")
        return cleaned


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    data: ProfileData
    completeness_score: int
    missing_blocks: list[str]
    updated_at: datetime
