import datetime
from typing import Literal
from pydantic import BaseModel, Field


class StatisticWidgetSettings(BaseModel):
    id: int
    title: str
    user: int
    type: Literal["top_donators", "last_donations"]

    period: str
    elements_count: int
    view_type: str
    string_template: str

    font: str
    color: str
    style: str
    font_align: str
    font_size: int

    shadow_color: str
    shadow_horizontal_offset: int
    shadow_vertical_offset: int
    shadow_blur: int

    contour_color: str
    contour_width: int

    created_at: datetime.datetime
    updated_at: datetime.datetime


class ModerationSettings(BaseModel):
    id: int
    is_active: bool = Field(False)
    duration: int
    is_manual: bool = Field(False)
    activation_amount: str = Field("")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def need_moderation(self, amount: str) -> bool:
        return self.is_active and self.activation_amount is not None and self.activation_amount <= amount
    
    def is_manual_moderation_enabled(self, amount: str) -> bool:
        return self.need_moderation(amount) and self.is_manual
