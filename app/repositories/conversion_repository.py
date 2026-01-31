"""Repository: data access for Conversion."""

from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.conversion import Conversion


class ConversionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, conversion: Conversion) -> Conversion:
        self._db.add(conversion)
        self._db.commit()
        self._db.refresh(conversion)
        return conversion

    def count_by_user(self, user_id: UUID) -> int:
        return self._db.query(func.count(Conversion.id)).filter(Conversion.user_id == user_id).scalar() or 0

    def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversion]:
        return (
            self._db.query(Conversion)
            .filter(Conversion.user_id == user_id)
            .order_by(Conversion.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
