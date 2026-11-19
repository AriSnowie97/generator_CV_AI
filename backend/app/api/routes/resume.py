"""Resume editor, autosave, template preview, and profile sync endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.profile import ProfileData
from app.schemas.resume import ResumePreviewRequest, ResumeResponse, ResumeUpdateRequest
from app.services.html_templates import render_resume_html
from app.services.resume_service import (
    estimate_pages,
    get_or_create_resume,
    sync_resume_from_profile,
    update_resume,
)

router = APIRouter(prefix="/resume", tags=["resume"])


def _to_resume_response(resume) -> ResumeResponse:
    data = ProfileData.model_validate(resume.data_json or {})
    pages, warning = estimate_pages(data)
    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        title=resume.title,
        template_id=resume.template_id,
        language=resume.language,
        block_order=resume.block_order,
        data=data,
        estimated_pages=pages,
        page_warning=warning,
        updated_at=resume.updated_at,
    )


@router.get("", response_model=ResumeResponse)
def get_resume(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = get_or_create_resume(db, current_user)
    return _to_resume_response(resume)


@router.put("", response_model=ResumeResponse)
def put_resume(
    payload: ResumeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = update_resume(db, current_user, payload)
    return _to_resume_response(resume)


@router.post("/sync-from-profile", response_model=ResumeResponse)
def sync_from_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = sync_resume_from_profile(db, current_user)
    return _to_resume_response(resume)


@router.post("/preview-html", response_class=HTMLResponse)
def preview_html(payload: ResumePreviewRequest):
    """Render live ATS-friendly HTML preview (accessible for both users and guest demo)."""
    html_str = render_resume_html(payload.data, payload.template_id, payload.language, payload.block_order)
    return HTMLResponse(content=html_str)
