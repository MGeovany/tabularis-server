from pydantic import BaseModel


class UsageResponse(BaseModel):
    conversions_used: int
    conversions_limit: int
    plan: str
