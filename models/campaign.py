import datetime
from pydantic import BaseModel, Field


class Campaign(BaseModel):
    id: int
    author_id: int
    title: str
    description: str = Field("")
    target_amount: str
    collected_amount: str
    progress_percentage: float
    is_active: bool = Field(False)
    is_default: bool = Field(False)
    created_at: datetime.datetime
    updated_at: datetime.datetime
    start_at: datetime.datetime
    end_at: datetime.datetime
    is_active_now: bool = Field(False)
