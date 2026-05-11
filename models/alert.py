import datetime

from enum import Enum
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field


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


class ManualModerationAlertDecision(BaseModel):
    alert_id: int
    donation_id: int


class ActivationType(Enum):
    equal = "equal"
    over_equal = "over_equal"


class AlertSetting(BaseModel):
    id: int
    is_active: bool = Field(False)
    is_default: bool = Field(False)
    type_: str = Field(alias="type")

    activation_type: ActivationType | None = Field(None)
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

    def get_alert_duration_seconds(self) -> int:
        return int(self.sound_duration or 0) + int(self.message_duration or 0)


class AlertSettingsGroup(BaseModel):
    id: int
    title: str
    updated_at: datetime.datetime
    alert_settings: list[AlertSetting]

    def get_max_viewing_duration_seconds_by_amount(self, amount: str) -> int:
        try:
            amount_decimal = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            return 0

        duration = 0
        best_activation_amount = Decimal("-Infinity")

        for alert_setting in self.alert_settings:
            if not alert_setting.is_active:
                continue

            activation_amount: Decimal | None = None
            if alert_setting.activation_amount is not None:
                try:
                    activation_amount = Decimal(str(alert_setting.activation_amount))
                except (TypeError, ValueError, InvalidOperation):
                    activation_amount = None

            activation_type = alert_setting.activation_type
            if activation_type == ActivationType.equal:
                is_match = activation_amount is not None and amount_decimal == activation_amount
            elif activation_type == ActivationType.over_equal:
                is_match = activation_amount is not None and amount_decimal >= activation_amount
            else:
                is_match = True

            if not is_match:
                continue

            current_activation_amount = (
                activation_amount if activation_amount is not None else Decimal("-Infinity")
            )
            current_duration = alert_setting.get_alert_duration_seconds()

            if current_activation_amount > best_activation_amount:
                best_activation_amount = current_activation_amount
                duration = current_duration
            elif current_activation_amount == best_activation_amount:
                duration = max(duration, current_duration)

        return duration


class Alert(BaseModel):
    id: int
    author_id: int
    amount: float
    message: str = Field("")
    donor_name: str
    voice: str | None = Field(None)
    donation_id: int | None = Field(None)
    timestamp: datetime.datetime
    setting: AlertSetting | int | None = Field(None)


class BanWord(BaseModel):
    id: int
    is_active: bool = Field(False)
    words: str = Field("")
    created_at: datetime.datetime
    updated_at: datetime.datetime
