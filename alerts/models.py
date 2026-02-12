import datetime
from enum import Enum

from pydantic import BaseModel


class AlertSettings(BaseModel):
    max_message_length: int
    font_size: int
    min_amount: float
    enable_alerts: bool


class Alert(BaseModel):
    alert_id: int
    author_id: int
    amount: float
    message: str
    video_url: str
    sound_url: str
    alert_settings: AlertSettings
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


class WidgetTokenInfo(BaseModel):
    author_id: int
    iat: datetime.datetime
