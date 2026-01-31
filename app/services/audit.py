"""Audit logging: record actions to audit_logs table."""

import uuid
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    user_id: uuid.UUID | None,
    action: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()
