"""Account settings, GDPR data export, and full account deletion endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import AIRequestLog, EventLog, User
from app.schemas.auth import SettingsUpdateRequest, UserResponse
from app.services.auth_service import delete_user_account
from app.services.profile_service import get_or_create_profile
from app.services.resume_service import get_or_create_resume

router = APIRouter(prefix="/settings", tags=["settings"])


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.preferred_interface_language = payload.preferred_interface_language
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.get("/export-data")
def export_user_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export all personal data stored for the authenticated user as JSON."""
    profile = get_or_create_profile(db, current_user)
    resume = get_or_create_resume(db, current_user)
    ai_count = db.query(AIRequestLog).filter(AIRequestLog.user_id == current_user.id).count()
    events = [
        {"event_type": e.event_type, "created_at": e.created_at.isoformat()}
        for e in db.query(EventLog).filter(EventLog.user_id == current_user.id).order_by(EventLog.created_at.desc()).limit(50)
    ]

    bundle = {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "is_email_verified": current_user.is_email_verified,
            "preferred_interface_language": current_user.preferred_interface_language,
            "consent_accepted": current_user.consent_accepted,
            "created_at": current_user.created_at.isoformat(),
        },
        "profile": profile.data_json,
        "resume": {
            "title": resume.title,
            "template_id": resume.template_id,
            "language": resume.language,
            "block_order": resume.block_order,
            "data": resume.data_json,
        },
        "ai_requests_total": ai_count,
        "recent_events": events,
    }
    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": "attachment; filename=\"resumecraft_personal_data.json\""},
    )


@router.delete("/account")
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Permanently delete account, profile, resume, logs, and exported files."""
    delete_user_account(db, current_user)
    return {"status": "deleted", "message": "Акаунт та всі пов'язані дані остаточно видалено."}
