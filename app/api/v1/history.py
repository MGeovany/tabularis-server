from fastapi import APIRouter, Depends, Query
from typing import cast
from uuid import UUID

from app.dependencies import get_or_create_current_user, get_conversion_repo
from app.models.user import User
from app.repositories.conversion_repository import ConversionRepository
from app.schemas.conversion import ConversionItem, ConversionList

router = APIRouter()


@router.get("/history", response_model=ConversionList)
def history(
    current_user: User = Depends(get_or_create_current_user),
    conversion_repo: ConversionRepository = Depends(get_conversion_repo),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List conversions for the current user (Repository)."""
    user_id = cast(UUID, current_user.id)
    total = conversion_repo.count_by_user(user_id)
    rows = conversion_repo.list_by_user(user_id, limit=limit, offset=offset)
    return ConversionList(items=[ConversionItem.model_validate(r) for r in rows], total=total)
