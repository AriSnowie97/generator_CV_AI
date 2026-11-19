"""PDF and DOCX export routes."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.ai import ExportRequest
from app.schemas.profile import ProfileData
from app.services.export_service import export_resume_file
from app.services.resume_service import get_or_create_resume

router = APIRouter(prefix="/export", tags=["export"])


@router.post("")
def export_resume(
    payload: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = get_or_create_resume(db, current_user)
    data = payload.data or ProfileData.model_validate(resume.data_json or {})
    file_bytes, filename, media_type = export_resume_file(
        db=db,
        user=current_user,
        fmt=payload.format,
        template_id=payload.template_id or resume.template_id,
        language=payload.language or resume.language,
        block_order=payload.block_order or resume.block_order,
        data=data,
        use_ai_filename=payload.use_ai_filename,
    )
    encoded_name = quote(filename)
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_name}",
            "X-Export-Filename": filename,
        },
    )
