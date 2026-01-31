"""Repository: data access for AuditLog."""

import uuid
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        user_id: UUID | None,
        action: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            ip=ip,
            user_agent=user_agent,
        )
        self._db.add(entry)
        self._db.commit()
        return entry
