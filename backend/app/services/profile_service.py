"""User profile management, photo processing, and completeness scoring."""

import base64
import io

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import EventLog, Profile, Resume, User
from app.schemas.profile import ProfileData

MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def calculate_completeness(data: ProfileData) -> tuple[int, list[str]]:
    """Compute profile completeness percentage (0-100) and list missing blocks."""
    checks = [
        ("contacts", bool(data.contacts.full_name.strip() or (data.contacts.first_name.strip() and data.contacts.last_name.strip())) and bool(str(data.contacts.email or "").strip()), 20),
        ("target_role", bool(data.target_role.strip()), 15),
        ("summary", bool(data.summary.strip()), 15),
        ("experience", len(data.experiences) > 0, 20),
        ("education", len(data.education) > 0, 10),
        ("skills", (len(data.skills) + len(data.soft_skills)) > 0, 10),
        ("languages", len(data.languages) > 0, 5),
        ("links", len(data.links) > 0, 5),
    ]
    score = 0
    missing: list[str] = []
    for name, passed, weight in checks:
        if passed:
            score += weight
        else:
            missing.append(name)
    return score, missing


def get_or_create_profile(db: Session, user: User) -> Profile:
    """Return existing user profile or initialize an empty one."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile:
        return profile

    data = ProfileData()
    data.contacts.email = user.email
    score, _ = calculate_completeness(data)
    profile = Profile(user_id=user.id, data_json=data.model_dump(), completeness_score=score)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, user: User, data: ProfileData, sync_resume: bool = True) -> Profile:
    """Validate and save user profile, optionally syncing empty/matching resume."""
    profile = get_or_create_profile(db, user)
    # Normalize full_name if first/last provided
    if not data.contacts.full_name.strip() and (data.contacts.first_name.strip() or data.contacts.last_name.strip()):
        data.contacts.full_name = f"{data.contacts.first_name.strip()} {data.contacts.last_name.strip()}".strip()

    score, _ = calculate_completeness(data)
    profile.data_json = data.model_dump()
    profile.completeness_score = score

    if sync_resume:
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        if resume:
            resume.data_json = data.model_dump()

    db.add(EventLog(user_id=user.id, event_type="profile_updated", metadata_json={"score": score}))
    db.commit()
    db.refresh(profile)
    return profile


def process_photo_bytes(raw_bytes: bytes, content_type: str | None) -> str:
    """Validate uploaded image (type, size, magic bytes), fix EXIF rotation, crop to 320x320 JPEG data URI."""
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл зображення порожній")
    if len(raw_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Розмір фото не може перевищувати 5 МБ",
        )
    if content_type and content_type.lower() not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Підтримуються лише зображення JPG, PNG або WebP",
        )

    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(raw_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = bg
            else:
                img = img.convert("RGB")
            cropped = ImageOps.fit(img, (320, 320), method=Image.Resampling.LANCZOS)
            out = io.BytesIO()
            cropped.save(out, format="JPEG", quality=85, optimize=True)
            encoded = base64.b64encode(out.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не вдалося прочитати зображення. Переконайтеся, що це коректний JPG, PNG або WebP файл.",
        ) from exc


def set_profile_photo(db: Session, user: User, photo_data_uri: str) -> Profile:
    """Attach or remove profile photo and sync it directly into the user's resume."""
    profile = get_or_create_profile(db, user)
    p_data = ProfileData.model_validate(profile.data_json or {})
    p_data.contacts.photo_url = photo_data_uri
    profile.data_json = p_data.model_dump()

    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if resume:
        r_data = ProfileData.model_validate(resume.data_json or {})
        r_data.contacts.photo_url = photo_data_uri
        resume.data_json = r_data.model_dump()

    db.commit()
    db.refresh(profile)
    return profile
