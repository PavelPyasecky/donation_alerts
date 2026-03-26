import datetime

from pydantic import BaseModel


class Donater(BaseModel):
    donor_name: str
    total_amount: str
    total_count: int
    last_created_at: datetime.datetime
