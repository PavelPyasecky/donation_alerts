import datetime
from decimal import Decimal

from pydantic import BaseModel


class DonationEvent(BaseModel):
    donor_name: str
    amount: Decimal
    timestamp: datetime.datetime
    donation_id: int


class TopDonatersSettingInfo(BaseModel):
    setting_id: int
    author_id: int
    period: str
    elements_count: int
