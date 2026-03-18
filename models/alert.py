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
    setting: "AlertSetting" | None = Field(None)


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

    activation_type: str | None = Field(None)
    activation_amount: str | None = Field(None)
    sound_duration: int | None = Field(None)
    message_duration: int | None = Field(None)
    appear_effect: str | None = Field(None)
    disappear_effect: str | None = Field(None)
    image_position: str | None = Field(None)

    header_template: str | None = Field(None)
    header_font: str | None = Field(None)
    header_main_color: str | None = Field(None)
    header_additional_color: str | None = Field(None)
    header_font_size: int | None = Field(None)
    header_animation_type: str | None = Field(None)
    header_animation_objects: str | None = Field(None)
    header_animate_all_words: bool = Field(False)
    header_shadow_size: int | None = Field(None)
    header_contour_color: str | None = Field(None)
    header_enable_contour: bool = Field(False)

    body_template: str | None = Field(None)
    body_font: str | None = Field(None)
    body_main_color: str | None = Field(None)
    body_font_size: int | None = Field(None)
    body_shadow_size: int | None = Field(None)
    body_contour_color: str | None = Field(None)
    body_enable_contour: bool = Field(False)
    body_max_message_length: int | None = Field(None)

    content_type: str | None = Field(None)
    content: str | None = Field(None)
    content_animation_type: str

    music_file: str | None = Field(None)
    music_volume: int | None = Field(None)

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
