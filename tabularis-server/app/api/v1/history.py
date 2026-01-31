from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.conversion import Conversion
from app.schemas.conversion import ConversionItem, ConversionList
from sqlalchemy.orm import Session
from sqlalchemy import func

router = APIRouter()


@router.get("/history", response_model=ConversionList)
def history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List conversions for the current user, ordered by created_at descending."""
    total = db.query(func.count(Conversion.id)).filter(Conversion.user_id == current_user.id).scalar() or 0
    rows = (
        db.query(Conversion)
        .filter(Conversion.user_id == current_user.id)
        .order_by(Conversion.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ConversionList(items=[ConversionItem.model_validate(r) for r in rows], total=total)
