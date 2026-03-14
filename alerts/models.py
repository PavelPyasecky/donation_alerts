import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PageSettings(BaseModel):
    max_message_length: int
    font_size: int
    min_amount: float
    allow_message: bool
    video_min_amount: str


class Alert(BaseModel):
    id: int
    author_id: int
    amount: float
    message: str
    donor_name: str
    video_url: str
    sound_url: str
    alert_settings: PageSettings
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


class WidgetTokenInfo(BaseModel):
    author_id: int
    created_at: datetime.datetime
    control_uuid: str


class MessageTypes(Enum):
    alert_status = "alert_status"
    widget_status = "widget_status"


class WidgetStatus(BaseModel):
    is_online: bool


class WidgetMessage(BaseModel):
    type_: MessageTypes = Field(alias="type")
    data: AlertStatus | WidgetStatus


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


class RabbitMessageTypes(Enum):
    event = "event"
    update = "update"


class SkipAlert(BaseModel):
    author_id: int
    donation_id: int


class RabbitMessage(BaseModel):
    type_: RabbitMessageTypes = Field(alias="type")
    action: str
    data: Alert | Campaign | SkipAlert | list["AlertSetting"]


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
