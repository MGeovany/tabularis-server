from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversionItem(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    size_bytes: int
    status: str
    duration_ms: int | None
    error_message: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ConversionList(BaseModel):
    items: list[ConversionItem]
    total: int
