"""User profile CRUD and photo upload endpoints."""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.profile import ProfileData, ProfileResponse
from app.services.profile_service import (
    calculate_completeness,
    get_or_create_profile,
    process_photo_bytes,
    set_profile_photo,
    update_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _to_profile_response(profile) -> ProfileResponse:
    data = ProfileData.model_validate(profile.data_json or {})
    score, missing = calculate_completeness(data)
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        data=data,
        completeness_score=score,
        missing_blocks=missing,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(db, current_user)
    return _to_profile_response(profile)


@router.put("", response_model=ProfileResponse)
def put_profile(
    payload: ProfileData,
    sync_resume: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = update_profile(db, current_user, payload, sync_resume=sync_resume)
    return _to_profile_response(profile)


@router.post("/photo", response_model=ProfileResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload profile photo (JPG/PNG/WebP <= 5 MB) and automatically sync it into the resume."""
    raw = await file.read()
    photo_uri = process_photo_bytes(raw, file.content_type)
    profile = set_profile_photo(db, current_user, photo_uri)
    return _to_profile_response(profile)


@router.delete("/photo", response_model=ProfileResponse)
def remove_photo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove profile photo from both profile and resume."""
    profile = set_profile_photo(db, current_user, "")
    return _to_profile_response(profile)
