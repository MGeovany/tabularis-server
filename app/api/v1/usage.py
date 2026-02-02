from fastapi import APIRouter, Depends
from typing import cast
from uuid import UUID

from app.dependencies import get_or_create_current_user, get_conversion_repo
from app.models.user import User
from app.schemas.usage import UsageResponse
from app.repositories.conversion_repository import ConversionRepository
from app.services.usage_window import current_month_window

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def usage(
    current_user: User = Depends(get_or_create_current_user),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
) -> UsageResponse:
    """Return current user's usage: conversions_used, conversions_limit, plan."""
    window = current_month_window()
    user_id = cast(UUID, current_user.id)
    used = conversion_repo.count_success_by_user_since(user_id, window.period_start)
    plan = cast(str, current_user.plan)
    limit_raw = cast(int, current_user.conversions_limit)
    limit = limit_raw or (0 if plan.upper() == "PRO" else 10)
    return UsageResponse(
        conversions_used=used,
        conversions_limit=limit,
        plan=plan,
    )
