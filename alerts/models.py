import datetime
from enum import Enum

from pydantic import BaseModel


class AlertSettings(BaseModel):
    text_color: str
    font_size: int
    image_url: str
    sound_url: str
    animation_type: str
    min_amount: float


class Alert(BaseModel):
    alert_id: int
    author_id: int
    amount: float
    message: str
    settings: AlertSettings
    donation_id: int
    timestamp: datetime.datetime


class Statuses(Enum):
    error = "error"
    delivered = "delivered"


class AlertStatus(BaseModel):
    alert_id: int
    status: Statuses
    external_id: str
    delivered_at: datetime.datetime
