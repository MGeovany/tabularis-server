import io
import time
import uuid
from typing import cast
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, status, UploadFile
from fastapi.responses import StreamingResponse

from app.config import settings
from app.dependencies import (
    get_or_create_current_user,
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
from app.services import download_cache
from app.services.page_selection import parse_pages, validate_pages

router = APIRouter()

ALLOWED_CONTENT_TYPE = "application/pdf"


@router.post("/convert/pdf-info")
def pdf_info(
    file: UploadFile = File(...),
    current_user: User = Depends(get_or_create_current_user),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """Inspect a PDF (page count) to drive UI decisions (free/pro)."""
    check_can_convert(current_user, conversion_repo)

    if file.content_type and file.content_type.lower() != ALLOWED_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Only application/pdf is accepted."},
        )

    content = file.file.read()
    if len(content) > settings.max_pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY,
            detail={
                "message": f"File too large. Maximum size is {settings.max_pdf_bytes // (1024 * 1024)} MB.",
            },
        )

    # Absolute validation (corruption, absolute page cap)
    conversion_service.validate_pdf(content, file.content_type, max_pages=settings.max_pdf_pages)
    total_pages = conversion_service.get_page_count(content)

    plan = cast(str, current_user.plan)
    free_max = settings.free_max_pdf_pages
    max_select_pages = free_max if plan.upper() != "PRO" else settings.max_pdf_pages
    can_convert_all = plan.upper() == "PRO" or total_pages <= free_max

    return {
        "filename": file.filename or "document.pdf",
        "total_pages": total_pages,
        "plan": plan,
        "max_select_pages": max_select_pages,
        "can_convert_all": can_convert_all,
        "free_max_pages": free_max,
    }


@router.post("/convert/pdf-to-excel")
def pdf_to_excel(
    request: Request,
    file: UploadFile = File(...),
    pages: str | None = Form(None),
    current_user: User = Depends(get_or_create_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """Accept PDF upload, return XLSX stream. Does not store PDF."""
    user_id = cast(uuid.UUID, current_user.id)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"].split(",")[0].strip()

    log_audit(audit_repo, user_id, "CONVERSION_REQUEST", ip=ip, user_agent=user_agent)
    check_can_convert(current_user, conversion_repo)

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

    # Validate PDF early (corruption, absolute page cap)
    try:
        conversion_service.validate_pdf(content, file.content_type, max_pages=settings.max_pdf_pages)
        total_pages = conversion_service.get_page_count(content)
    except ConversionError as e:
        if e.code == "FILE_TOO_LARGE":
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY, detail=e.message)
        if e.code == "PAGE_LIMIT_EXCEEDED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

    conversion_id = uuid.uuid4()
    start = time.perf_counter()
    status_str = "success"
    duration_ms = 0
    plan = cast(str, current_user.plan)
    free_max_pages = settings.free_max_pdf_pages
    selected_pages: list[int] | None = None
    if pages and pages.strip():
        try:
            sel = parse_pages(pages).pages
            validate_pages(sel, total_pages=total_pages, max_selected=free_max_pages if plan.upper() != "PRO" else None)
            selected_pages = sel
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid page selection.", "total_pages": total_pages},
            )
    else:
        if plan.upper() != "PRO" and total_pages > free_max_pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Free plan supports up to {free_max_pages} pages per conversion. Select pages or upgrade to Pro.",
                    "total_pages": total_pages,
                    "max_pages": free_max_pages,
                },
            )

    try:
        xlsx_bytes, duration_sec = conversion_service.convert_to_excel(
            content,
            filename,
            content_type=file.content_type,
            pages=selected_pages,
        )
        duration_ms = int(duration_sec * 1000)
    except ConversionError as e:
        status_str = "failed"
        error_message = (e.message or str(e))[:1024]
        duration_ms = int((time.perf_counter() - start) * 1000)
        conversion_repo.create(
            Conversion(
                id=conversion_id,
                user_id=user_id,
                filename=filename,
                size_bytes=size_bytes,
                status=status_str,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        )
        log_audit(audit_repo, user_id, "CONVERSION_FAILED", ip=ip, user_agent=user_agent)
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
                user_id=user_id,
                filename=filename,
                size_bytes=size_bytes,
                status=status_str,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        )
        log_audit(audit_repo, user_id, "CONVERSION_FAILED", ip=ip, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversion failed. The PDF may be unsupported or corrupted.",
        )

    conversion_repo.create(
        Conversion(
            id=conversion_id,
            user_id=user_id,
            filename=filename,
            size_bytes=size_bytes,
            status=status_str,
            duration_ms=duration_ms,
            error_message=None,
        )
    )
    log_audit(audit_repo, user_id, "CONVERSION_SUCCESS", ip=ip, user_agent=user_agent)

    # Allow short-lived re-download from history UI.
    download_cache.put(conversion_id, xlsx_bytes)

    out_name = (filename.rsplit(".", 1)[0] if "." in filename else filename) + ".xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "X-Conversion-Id": str(conversion_id),
        },
    )


@router.get("/convert/{conversion_id}/download")
def download_converted_xlsx(
    conversion_id: uuid.UUID,
    current_user: User = Depends(get_or_create_current_user),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
):
    """Re-download a recently converted XLSX (short-lived cache)."""
    conv = conversion_repo.get_by_id(conversion_id)
    user_id = cast(uuid.UUID, current_user.id)
    if not conv or cast(uuid.UUID, conv.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    xlsx_bytes = download_cache.get(conversion_id)
    if not xlsx_bytes:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download expired. Please convert the PDF again.",
        )

    out_name = (conv.filename.rsplit(".", 1)[0] if "." in conv.filename else conv.filename) + ".xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
