"""Usage limits: check and increment conversions per user/plan."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User


class UsageLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Usage limit reached. Please upgrade to Pro."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def can_convert(user: User) -> bool:
    """Return True if user has remaining conversions (FREE: 10, PRO: limit or unlimited)."""
    if user.plan == "PRO" and user.conversions_limit <= 0:
        return True  # unlimited
    return user.conversions_used < user.conversions_limit


def check_can_convert(user: User) -> None:
    """Raise UsageLimitExceeded if user cannot perform another conversion."""
    if not can_convert(user):
        raise UsageLimitExceeded(
            detail="Usage limit reached. Please upgrade to Pro to continue converting."
        )


def increment_usage(db: Session, user: User) -> None:
    """Increment user.conversions_used by 1. Commit is caller's responsibility."""
    user.conversions_used = (user.conversions_used or 0) + 1
    db.add(user)
    db.commit()
