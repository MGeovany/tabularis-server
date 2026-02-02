from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class UserMe(BaseModel):
    id: UUID
    email: str | None
    plan: str
    conversions_used: int
    conversions_limit: int
    reset_at: datetime
    created_at: datetime | None

    model_config = {"from_attributes": True}
