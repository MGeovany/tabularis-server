from fastapi import APIRouter, Depends
from typing import cast

from app.dependencies import get_or_create_current_user
from app.models.user import User
from app.schemas.usage import UsageResponse

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def usage(current_user: User = Depends(get_or_create_current_user)) -> UsageResponse:
    """Return current user's usage: conversions_used, conversions_limit, plan."""
    return UsageResponse(
        conversions_used=cast(int, current_user.conversions_used or 0),
        conversions_limit=cast(int, current_user.conversions_limit),
        plan=cast(str, current_user.plan),
    )
