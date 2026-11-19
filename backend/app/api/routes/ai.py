"""AI assistant routes with daily quota tracking and confirmation-only suggestions."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.ai import (
    AIEditTextRequest,
    AIFilenameRequest,
    AIFilenameResponse,
    AIGenerateSummaryRequest,
    AIImproveBulletRequest,
    AIQuotaInfo,
    AISuggestionsResponse,
)
from app.services.ai_service import (
    edit_selected_text,
    generate_resume_filename,
    generate_summary,
    get_ai_quota,
    improve_bullet,
)

router = APIRouter(prefix="/ai", tags=["ai"])

DISCLAIMER_UK = "Перевірте запропоновані варіанти перед збереженням. AI не вигадує факти; позначку «уточніть» замініть реальними даними."
DISCLAIMER_EN = "Review suggested options before applying. AI does not invent facts; replace «уточніть» placeholders with real metrics."


@router.get("/quota", response_model=AIQuotaInfo)
def quota(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_ai_quota(db, current_user)


@router.post("/improve-bullet", response_model=AISuggestionsResponse)
def api_improve_bullet(
    payload: AIImproveBulletRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    variants, provider, q = improve_bullet(db, current_user, payload)
    disclaimer = DISCLAIMER_UK if payload.language == "uk" else DISCLAIMER_EN
    return AISuggestionsResponse(variants=variants, provider=provider, quota=q, disclaimer=disclaimer)


@router.post("/generate-summary", response_model=AISuggestionsResponse)
def api_generate_summary(
    payload: AIGenerateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    variants, provider, q = generate_summary(db, current_user, payload)
    disclaimer = DISCLAIMER_UK if payload.language == "uk" else DISCLAIMER_EN
    return AISuggestionsResponse(variants=variants, provider=provider, quota=q, disclaimer=disclaimer)


@router.post("/edit-text", response_model=AISuggestionsResponse)
def api_edit_text(
    payload: AIEditTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    variants, provider, q = edit_selected_text(db, current_user, payload)
    disclaimer = DISCLAIMER_UK if payload.language == "uk" else DISCLAIMER_EN
    return AISuggestionsResponse(variants=variants, provider=provider, quota=q, disclaimer=disclaimer)


@router.post("/filename", response_model=AIFilenameResponse)
def api_generate_filename(
    payload: AIFilenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename, provider, q = generate_resume_filename(db, current_user, payload, count_quota=True)
    return AIFilenameResponse(filename=filename, provider=provider, quota=q)
