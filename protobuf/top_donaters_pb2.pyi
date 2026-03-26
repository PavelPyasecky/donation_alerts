from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RetrieveTopDonatersSettingRequest(_message.Message):
    __slots__ = ("author_id", "setting_id")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    SETTING_ID_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    setting_id: int
    def __init__(self, author_id: _Optional[int] = ..., setting_id: _Optional[int] = ...) -> None: ...

class TopDonatersSetting(_message.Message):
    __slots__ = ("id", "user", "title", "period", "elements_count", "view_type", "string_template", "font", "color", "style", "font_align", "font_size", "shadow_color", "shadow_horizontal_offset", "shadow_vertical_offset", "shadow_blur", "contour_color", "contour_width", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    ELEMENTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    VIEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    STRING_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    FONT_FIELD_NUMBER: _ClassVar[int]
    COLOR_FIELD_NUMBER: _ClassVar[int]
    STYLE_FIELD_NUMBER: _ClassVar[int]
    FONT_ALIGN_FIELD_NUMBER: _ClassVar[int]
    FONT_SIZE_FIELD_NUMBER: _ClassVar[int]
    SHADOW_COLOR_FIELD_NUMBER: _ClassVar[int]
    SHADOW_HORIZONTAL_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SHADOW_VERTICAL_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SHADOW_BLUR_FIELD_NUMBER: _ClassVar[int]
    CONTOUR_COLOR_FIELD_NUMBER: _ClassVar[int]
    CONTOUR_WIDTH_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: int
    user: int
    title: str
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
    created_at: str
    updated_at: str
    def __init__(self, id: _Optional[int] = ..., user: _Optional[int] = ..., title: _Optional[str] = ..., period: _Optional[str] = ..., elements_count: _Optional[int] = ..., view_type: _Optional[str] = ..., string_template: _Optional[str] = ..., font: _Optional[str] = ..., color: _Optional[str] = ..., style: _Optional[str] = ..., font_align: _Optional[str] = ..., font_size: _Optional[int] = ..., shadow_color: _Optional[str] = ..., shadow_horizontal_offset: _Optional[int] = ..., shadow_vertical_offset: _Optional[int] = ..., shadow_blur: _Optional[int] = ..., contour_color: _Optional[str] = ..., contour_width: _Optional[int] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...
