"""Resume editor and template schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.profile import ProfileData

TemplateId = Literal["minimal", "classic", "it"]
ResumeLanguage = Literal["uk", "en"]
DEFAULT_BLOCK_ORDER = ["summary", "experience", "education", "courses", "skills", "languages", "links"]
ALLOWED_BLOCKS = set(DEFAULT_BLOCK_ORDER)


class ResumeUpdateRequest(BaseModel):
    title: str = Field(default="Моє резюме", min_length=1, max_length=255)
    template_id: TemplateId = "minimal"
    language: ResumeLanguage = "uk"
    block_order: list[str] = Field(default_factory=lambda: list(DEFAULT_BLOCK_ORDER))
    data: ProfileData = Field(default_factory=ProfileData)

    @field_validator("block_order")
    @classmethod
    def validate_block_order(cls, v: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in v:
            if item in ALLOWED_BLOCKS and item not in deduped:
                deduped.append(item)
        for default_item in DEFAULT_BLOCK_ORDER:
            if default_item not in deduped:
                deduped.append(default_item)
        return deduped


class ResumeResponse(BaseModel):
    id: str
    user_id: str
    title: str
    template_id: TemplateId
    language: ResumeLanguage
    block_order: list[str]
    data: ProfileData
    estimated_pages: int
    page_warning: bool
    updated_at: datetime


class ResumePreviewRequest(BaseModel):
    template_id: TemplateId = "minimal"
    language: ResumeLanguage = "uk"
    block_order: list[str] = Field(default_factory=lambda: list(DEFAULT_BLOCK_ORDER))
    data: ProfileData = Field(default_factory=ProfileData)
    show_branding: bool = True
