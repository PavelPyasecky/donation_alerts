import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Alert(BaseModel):
    id: int
    author_id: int
    amount: float
    message: str
    donor_name: str
    video_url: str
    voice: str
    donation_id: int | None = Field(None)
    timestamp: datetime.datetime


class Statuses(Enum):
    error = "error"
    delivered = "delivered"


class AlertStatus(BaseModel):
    alert_id: int
    status: Statuses
    delivered_at: datetime.datetime


class RabbitMQAlertStatus(AlertStatus):
    author_id: int


class SkipAlert(BaseModel):
    author_id: int
    donation_id: int


class AlertSetting(BaseModel):
    id: int
    is_active: bool = Field(False)
    type_: str = Field(alias="type")

    activation_type: str
    activation_amount: str
    sound_duration: int
    message_duration: int
    appear_effect: str
    disappear_effect: str
    image_position: str

    header_template: str
    header_font: str
    header_main_color: str
    header_additional_color: str
    header_font_size: int
    header_animation_type: str
    header_animation_objects: str
    header_animate_all_words: bool = Field(False)
    header_shadow_size: int
    header_contour_color: str
    header_enable_contour: bool = Field(False)

    body_template: str
    body_font: str
    body_main_color: str
    body_font_size: int
    body_shadow_size: int
    body_contour_color: str
    body_enable_contour: bool = Field(False)
    body_max_message_length: int

    content_type: str
    content: str | None = Field(None)
    content_animation_type: str

    music_file: str | None = Field(None)
    music_volume: int

    speech_synthesis_is_enabled: bool | None = Field(None)
    speech_synthesis_min_amount: str | None = Field(None)
    speech_synthesis_volume: int | None = Field(None)
    speech_synthesis_start_type: str | None = Field(None)
    speech_synthesis_voice: int | None = Field(None)

    created_at: datetime.datetime
    updated_at: datetime.datetime


class AlertSettingsGroup(BaseModel):
    id: int
    title: str
    updated_at: datetime.datetime
    alert_settings: list[AlertSetting]

