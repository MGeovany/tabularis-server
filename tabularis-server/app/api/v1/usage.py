from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.usage import UsageResponse

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def usage(current_user: User = Depends(get_current_user)) -> UsageResponse:
    """Return current user's usage: conversions_used, conversions_limit, plan."""
    return UsageResponse(
        conversions_used=current_user.conversions_used or 0,
        conversions_limit=current_user.conversions_limit,
        plan=current_user.plan,
    )
