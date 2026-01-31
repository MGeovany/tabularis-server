"""Audit: delegate to AuditLogRepository."""

from uuid import UUID

from app.repositories.audit_log_repository import AuditLogRepository


def log_audit(
    repo: AuditLogRepository,
    user_id: UUID | None,
    action: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    repo.create(user_id=user_id, action=action, ip=ip, user_agent=user_agent)
