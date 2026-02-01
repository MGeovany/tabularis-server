from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import verify_supabase_jwt
from app.logging_config import get_logger
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.conversion_repository import ConversionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.conversion import ConversionService
from app.strategies.table_extraction import PdfplumberTableExtractor

security = HTTPBearer(auto_error=False)
logger = get_logger("app.auth")


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_conversion_repo(db: Session = Depends(get_db)) -> ConversionRepository:
    return ConversionRepository(db)


def get_audit_repo(db: Session = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_conversion_service() -> ConversionService:
    return ConversionService(table_extractor=PdfplumberTableExtractor())


def _user_id_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request | None = None,
) -> UUID:
    if not credentials or not credentials.credentials:
        if request:
            logger.info("Auth missing credentials %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_supabase_jwt(credentials.credentials)
    if not payload:
        if request:
            logger.info("Auth invalid token %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        if request:
            logger.info("Auth missing sub claim %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return UUID(user_id_raw)
    except (ValueError, TypeError):
        if request:
            logger.info("Auth invalid sub uuid %s %s sub=%r", request.method, request.url.path, user_id_raw)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    user_id = _user_id_from_credentials(credentials, request=request)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def get_or_create_current_user(
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    user_id = _user_id_from_credentials(credentials, request=request)
    user = repo.get_by_id(user_id)
    if user:
        return user
    # `_user_id_from_credentials` has already validated credentials/token. This is defensive.
    if not credentials or not credentials.credentials:
        logger.info("Auth missing credentials (post-validate) %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_supabase_jwt(credentials.credentials)
    if payload is None:
        logger.info("Auth invalid token (post-validate) %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("email") or payload.get("email_address")
    user = User(
        id=user_id,
        email=email,
        plan="FREE",
        conversions_limit=10,
        conversions_used=0,
    )
    return repo.create(user)
