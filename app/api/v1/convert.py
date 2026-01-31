import io
import time
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Request, status, UploadFile
from fastapi.responses import StreamingResponse

from app.config import settings
from app.dependencies import (
    get_current_user,
    get_user_repo,
    get_conversion_repo,
    get_audit_repo,
    get_conversion_service,
)
from app.models.user import User
from app.models.conversion import Conversion
from app.repositories.user_repository import UserRepository
from app.repositories.conversion_repository import ConversionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.conversion import ConversionService, ConversionError
from app.services.usage_limits import check_can_convert, UsageLimitExceeded
from app.services.audit import log_audit

router = APIRouter()

ALLOWED_CONTENT_TYPE = "application/pdf"


@router.post("/convert/pdf-to-excel")
def pdf_to_excel(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """Accept PDF upload, return XLSX stream. Does not store PDF."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"].split(",")[0].strip()

    log_audit(audit_repo, current_user.id, "CONVERSION_REQUEST", ip=ip, user_agent=user_agent)
    check_can_convert(current_user)

    if file.content_type and file.content_type.lower() != ALLOWED_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only application/pdf is accepted.",
        )

    content = file.file.read()
    size_bytes = len(content)
    filename = file.filename or "document.pdf"

    if size_bytes > settings.max_pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY,
            detail=f"File too large. Maximum size is {settings.max_pdf_bytes // (1024 * 1024)} MB.",
        )

    conversion_id = uuid.uuid4()
    start = time.perf_counter()
    status_str = "success"
    duration_ms = 0

    try:
        xlsx_bytes, duration_sec = conversion_service.convert_to_excel(
            content,
            filename,
            content_type=file.content_type,
        )
        duration_ms = int(duration_sec * 1000)
    except ConversionError as e:
        status_str = "failed"
        error_message = (e.message or str(e))[:1024]
        duration_ms = int((time.perf_counter() - start) * 1000)
        conversion_repo.create(
            Conversion(
                id=conversion_id,
                user_id=current_user.id,
                filename=filename,
                size_bytes=size_bytes,
                status=status_str,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        )
        log_audit(audit_repo, current_user.id, "CONVERSION_FAILED", ip=ip, user_agent=user_agent)
        if e.code == "FILE_TOO_LARGE" or e.code == "PAGE_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY if e.code == "FILE_TOO_LARGE" else status.HTTP_400_BAD_REQUEST,
                detail=e.message,
            )
        if e.code == "NO_TABLE_DETECTED":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except UsageLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        status_str = "failed"
        error_message = str(e)[:1024]
        duration_ms = int((time.perf_counter() - start) * 1000)
        conversion_repo.create(
            Conversion(
                id=conversion_id,
                user_id=current_user.id,
                filename=filename,
                size_bytes=size_bytes,
                status=status_str,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        )
        log_audit(audit_repo, current_user.id, "CONVERSION_FAILED", ip=ip, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversion failed. The PDF may be unsupported or corrupted.",
        )

    conversion_repo.create(
        Conversion(
            id=conversion_id,
            user_id=current_user.id,
            filename=filename,
            size_bytes=size_bytes,
            status=status_str,
            duration_ms=duration_ms,
            error_message=None,
        )
    )
    user_repo.increment_conversions_used(current_user)
    log_audit(audit_repo, current_user.id, "CONVERSION_SUCCESS", ip=ip, user_agent=user_agent)

    out_name = (filename.rsplit(".", 1)[0] if "." in filename else filename) + ".xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
