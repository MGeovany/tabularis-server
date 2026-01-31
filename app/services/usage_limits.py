"""Usage limits: delegate to Policy (Free/Pro) and UserRepository for increment."""

from fastapi import HTTPException, status

from app.models.user import User
from app.policies.usage_policy import get_usage_policy


class UsageLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Usage limit reached. Please upgrade to Pro."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def check_can_convert(user: User) -> None:
    """Raise UsageLimitExceeded if user cannot convert (Policy)."""
    policy = get_usage_policy(user.plan)
    if not policy.can_convert(user):
        raise UsageLimitExceeded(detail=policy.limit_exceeded_message())
