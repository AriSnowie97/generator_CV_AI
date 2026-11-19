"""Resume editor persistence, page-length estimation, and profile sync."""

from sqlalchemy.orm import Session

from app.models.models import EventLog, Profile, Resume, User
from app.schemas.profile import ProfileData
from app.schemas.resume import DEFAULT_BLOCK_ORDER, ResumeUpdateRequest


def estimate_pages(data: ProfileData) -> tuple[int, bool]:
    """Estimate A4 page count from resume content length.

    Returns `(estimated_pages, page_warning)` where `page_warning` is True when > 2 pages.
    """
    char_count = len(data.summary or "") + len(data.target_role or "")
    for exp in data.experiences:
        char_count += len(exp.company) + len(exp.position) + sum(len(b) for b in exp.bullets) + 60
    for edu in data.education:
        char_count += len(edu.institution) + len(edu.degree) + len(edu.field_of_study) + 50
    char_count += sum(len(s) + 4 for s in data.skills)
    char_count += len(data.languages) * 25 + len(data.links) * 40

    line_budget = len(data.experiences) * 3 + len(data.education) * 2 + (char_count // 75)
    if line_budget <= 42 and char_count <= 2600:
        pages = 1
    elif line_budget <= 84 and char_count <= 5200:
        pages = 2
    else:
        pages = max(3, (char_count // 2500) + 1)
    return pages, pages > 2


def get_or_create_resume(db: Session, user: User) -> Resume:
    """Return user's single MVP resume, creating it from profile if absent."""
    resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    if resume:
        return resume

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    initial_data = profile.data_json if profile else ProfileData().model_dump()
    resume = Resume(
        user_id=user.id,
        title="Моє резюме",
        template_id="minimal",
        language="uk",
        block_order=list(DEFAULT_BLOCK_ORDER),
        data_json=initial_data,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def update_resume(db: Session, user: User, payload: ResumeUpdateRequest) -> Resume:
    """Save or autosave resume template, language, block order, and content."""
    resume = get_or_create_resume(db, user)
    resume.title = payload.title
    resume.template_id = payload.template_id
    resume.language = payload.language
    resume.block_order = payload.block_order
    resume.data_json = payload.data.model_dump()

    db.add(
        EventLog(
            user_id=user.id,
            event_type="resume_saved",
            metadata_json={"template_id": payload.template_id, "language": payload.language},
        )
    )
    db.commit()
    db.refresh(resume)
    return resume


def sync_resume_from_profile(db: Session, user: User) -> Resume:
    """Pull latest profile data into the user's resume while preserving template & block order."""
    resume = get_or_create_resume(db, user)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile:
        resume.data_json = profile.data_json
        db.commit()
        db.refresh(resume)
    return resume
