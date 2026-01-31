from fastapi import APIRouter, Depends

from app.dependencies import get_or_create_current_user
from app.models.user import User
from app.schemas.user import UserMe

router = APIRouter()


@router.get("/me", response_model=UserMe)
def me(current_user: User = Depends(get_or_create_current_user)) -> User:
    return current_user
