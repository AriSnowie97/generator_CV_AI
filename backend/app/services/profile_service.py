"""User profile management and completeness scoring."""

from sqlalchemy.orm import Session

from app.models.models import EventLog, Profile, Resume, User
from app.schemas.profile import ProfileData


def calculate_completeness(data: ProfileData) -> tuple[int, list[str]]:
    """Compute profile completeness percentage (0-100) and list missing blocks."""
    checks = [
        ("contacts", bool(data.contacts.full_name.strip() or (data.contacts.first_name.strip() and data.contacts.last_name.strip())) and bool(str(data.contacts.email or "").strip()), 20),
        ("target_role", bool(data.target_role.strip()), 15),
        ("summary", bool(data.summary.strip()), 15),
        ("experience", len(data.experiences) > 0, 20),
        ("education", len(data.education) > 0, 10),
        ("skills", len(data.skills) > 0, 10),
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
