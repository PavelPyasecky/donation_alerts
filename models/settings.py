import datetime
from pydantic import BaseModel, Field


class TopDonatersSettings(BaseModel):
    id: int
    title: str
    user: int

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
    activation_amount: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
