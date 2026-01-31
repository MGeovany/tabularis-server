"""Repository: data access for User."""

from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._db.query(User).filter(User.id == user_id).first()

    def create(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def increment_conversions_used(self, user: User) -> None:
        user.conversions_used = (user.conversions_used or 0) + 1
        self._db.add(user)
        self._db.commit()
