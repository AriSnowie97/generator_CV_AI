"""AI assistant request and response schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeLanguage


class AIImproveBulletRequest(BaseModel):
    bullet: str = Field(min_length=3, max_length=600)
    role_title: str = Field(default="", max_length=120)
    company: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=30)
    language: ResumeLanguage = "uk"


class AIGenerateSummaryRequest(BaseModel):
    target_role: str = Field(default="", max_length=120)
    experiences_summary: list[str] = Field(default_factory=list, max_length=15)
    skills: list[str] = Field(default_factory=list, max_length=30)
    languages: list[str] = Field(default_factory=list, max_length=10)
    language: ResumeLanguage = "uk"


class AIEditTextRequest(BaseModel):
    selected_text: str = Field(min_length=3, max_length=1500)
    instruction: str = Field(default="Зроби формулювання чіткішим і професійнішим", max_length=300)
    language: ResumeLanguage = "uk"


class AIFilenameRequest(BaseModel):
    first_name: str = Field(default="", max_length=60)
    last_name: str = Field(default="", max_length=60)
    full_name: str = Field(default="", max_length=120)
    target_role: str = Field(default="", max_length=120)
    format: Literal["pdf", "docx"] = "pdf"


class AIQuotaInfo(BaseModel):
    daily_limit: int
    used_today: int
    remaining_today: int
    reset_at: datetime


class AISuggestionsResponse(BaseModel):
    variants: list[str]
    provider: str
    quota: AIQuotaInfo
    disclaimer: str


class AIFilenameResponse(BaseModel):
    filename: str
    provider: str
    quota: AIQuotaInfo


class ExportRequest(BaseModel):
    format: Literal["pdf", "docx"]
    template_id: Literal["minimal", "classic", "it"] = "minimal"
    language: ResumeLanguage = "uk"
    block_order: list[str] = Field(default_factory=lambda: ["summary", "experience", "education", "skills", "languages", "links"])
    data: Optional[ProfileData] = None
    use_ai_filename: bool = True
    show_branding: bool = True
