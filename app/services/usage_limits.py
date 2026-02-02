"""Usage limits: monthly conversion enforcement (Free/Pro)."""

from fastapi import HTTPException, status
from typing import cast
from uuid import UUID

from app.models.user import User
from app.policies.usage_policy import get_usage_policy
from app.repositories.conversion_repository import ConversionRepository
from app.services.usage_window import current_month_window


class UsageLimitExceeded(HTTPException):
    def __init__(self, *, message: str, reset_at_iso: str | None = None, used: int | None = None, limit: int | None = None):
        payload: dict = {"message": message}
        if reset_at_iso:
            payload["reset_at"] = reset_at_iso
        if used is not None:
            payload["used"] = used
        if limit is not None:
            payload["limit"] = limit
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=payload)


def check_can_convert(user: User, conversion_repo: ConversionRepository) -> None:
    """Raise UsageLimitExceeded if user cannot convert under current monthly window."""
    window = current_month_window()
    user_id = cast(UUID, user.id)
    used = conversion_repo.count_success_by_user_since(user_id, window.period_start)

    plan_raw = cast(str, user.plan)
    plan = plan_raw or "FREE"
    policy = get_usage_policy(plan)

    # Pro policy can still use conversions_limit when configured.
    if plan.upper() == "PRO":
        limit_raw = cast(int, user.conversions_limit)
        limit = limit_raw or 0
        if limit <= 0:
            return
        if used >= limit:
            raise UsageLimitExceeded(
                message=policy.limit_exceeded_message(),
                reset_at_iso=window.reset_at.isoformat(),
                used=used,
                limit=limit,
            )
        return

    # Free: fixed 10/month by default.
    limit_raw = cast(int, user.conversions_limit)
    limit = limit_raw or 10
    if used >= limit:
        raise UsageLimitExceeded(
            message=policy.limit_exceeded_message(),
            reset_at_iso=window.reset_at.isoformat(),
            used=used,
            limit=limit,
        )
