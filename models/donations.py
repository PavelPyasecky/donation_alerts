import datetime

from pydantic import BaseModel, Field


class Donater(BaseModel):
    donor_name: str = Field("")
    total_amount: str
    total_count: int
    last_created_at: datetime.datetime


class Donation(BaseModel):
    id: int
    donor_name: str = Field("")
    amount: str
    created_at: datetime.datetime
