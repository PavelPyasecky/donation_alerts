from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AlertSetting(_message.Message):
    __slots__ = ("id", "is_active", "type", "activation_type", "activation_amount", "sound_duration", "message_duration", "appear_effect", "disappear_effect", "image_position", "header_template", "header_font", "header_main_color", "header_additional_color", "header_font_size", "header_animation_type", "header_animation_objects", "header_animate_all_words", "header_shadow_size", "header_contour_color", "header_enable_contour", "body_template", "body_font", "body_main_color", "body_font_size", "body_shadow_size", "body_contour_color", "body_enable_contour", "body_max_message_length", "content_type", "content", "content_animation_type", "music_file", "music_volume", "speech_synthesis_is_enabled", "speech_synthesis_min_amount", "speech_synthesis_volume", "speech_synthesis_start_type", "created_at", "updated_at", "group", "speech_synthesis_voice")
    ID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTIVATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTIVATION_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    SOUND_DURATION_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_DURATION_FIELD_NUMBER: _ClassVar[int]
    APPEAR_EFFECT_FIELD_NUMBER: _ClassVar[int]
    DISAPPEAR_EFFECT_FIELD_NUMBER: _ClassVar[int]
    IMAGE_POSITION_FIELD_NUMBER: _ClassVar[int]
    HEADER_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    HEADER_FONT_FIELD_NUMBER: _ClassVar[int]
    HEADER_MAIN_COLOR_FIELD_NUMBER: _ClassVar[int]
    HEADER_ADDITIONAL_COLOR_FIELD_NUMBER: _ClassVar[int]
    HEADER_FONT_SIZE_FIELD_NUMBER: _ClassVar[int]
    HEADER_ANIMATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    HEADER_ANIMATION_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    HEADER_ANIMATE_ALL_WORDS_FIELD_NUMBER: _ClassVar[int]
    HEADER_SHADOW_SIZE_FIELD_NUMBER: _ClassVar[int]
    HEADER_CONTOUR_COLOR_FIELD_NUMBER: _ClassVar[int]
    HEADER_ENABLE_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    BODY_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    BODY_FONT_FIELD_NUMBER: _ClassVar[int]
    BODY_MAIN_COLOR_FIELD_NUMBER: _ClassVar[int]
    BODY_FONT_SIZE_FIELD_NUMBER: _ClassVar[int]
    BODY_SHADOW_SIZE_FIELD_NUMBER: _ClassVar[int]
    BODY_CONTOUR_COLOR_FIELD_NUMBER: _ClassVar[int]
    BODY_ENABLE_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    BODY_MAX_MESSAGE_LENGTH_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_ANIMATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    MUSIC_FILE_FIELD_NUMBER: _ClassVar[int]
    MUSIC_VOLUME_FIELD_NUMBER: _ClassVar[int]
    SPEECH_SYNTHESIS_IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    SPEECH_SYNTHESIS_MIN_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    SPEECH_SYNTHESIS_VOLUME_FIELD_NUMBER: _ClassVar[int]
    SPEECH_SYNTHESIS_START_TYPE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    SPEECH_SYNTHESIS_VOICE_FIELD_NUMBER: _ClassVar[int]
    id: int
    is_active: bool
    type: str
    activation_type: str
    activation_amount: str
    sound_duration: float
    message_duration: float
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
    header_animate_all_words: bool
    header_shadow_size: int
    header_contour_color: str
    header_enable_contour: bool
    body_template: str
    body_font: str
    body_main_color: str
    body_font_size: int
    body_shadow_size: int
    body_contour_color: str
    body_enable_contour: bool
    body_max_message_length: int
    content_type: str
    content: str
    content_animation_type: str
    music_file: str
    music_volume: int
    speech_synthesis_is_enabled: bool
    speech_synthesis_min_amount: str
    speech_synthesis_volume: int
    speech_synthesis_start_type: str
    created_at: str
    updated_at: str
    group: int
    speech_synthesis_voice: int
    def __init__(self, id: _Optional[int] = ..., is_active: bool = ..., type: _Optional[str] = ..., activation_type: _Optional[str] = ..., activation_amount: _Optional[str] = ..., sound_duration: _Optional[float] = ..., message_duration: _Optional[float] = ..., appear_effect: _Optional[str] = ..., disappear_effect: _Optional[str] = ..., image_position: _Optional[str] = ..., header_template: _Optional[str] = ..., header_font: _Optional[str] = ..., header_main_color: _Optional[str] = ..., header_additional_color: _Optional[str] = ..., header_font_size: _Optional[int] = ..., header_animation_type: _Optional[str] = ..., header_animation_objects: _Optional[str] = ..., header_animate_all_words: bool = ..., header_shadow_size: _Optional[int] = ..., header_contour_color: _Optional[str] = ..., header_enable_contour: bool = ..., body_template: _Optional[str] = ..., body_font: _Optional[str] = ..., body_main_color: _Optional[str] = ..., body_font_size: _Optional[int] = ..., body_shadow_size: _Optional[int] = ..., body_contour_color: _Optional[str] = ..., body_enable_contour: bool = ..., body_max_message_length: _Optional[int] = ..., content_type: _Optional[str] = ..., content: _Optional[str] = ..., content_animation_type: _Optional[str] = ..., music_file: _Optional[str] = ..., music_volume: _Optional[int] = ..., speech_synthesis_is_enabled: bool = ..., speech_synthesis_min_amount: _Optional[str] = ..., speech_synthesis_volume: _Optional[int] = ..., speech_synthesis_start_type: _Optional[str] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ..., group: _Optional[int] = ..., speech_synthesis_voice: _Optional[int] = ...) -> None: ...

class AlertSettingsGroup(_message.Message):
    __slots__ = ("id", "title", "updated_at", "user", "alert_settings")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ALERT_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    id: int
    title: str
    updated_at: str
    user: int
    alert_settings: _containers.RepeatedCompositeFieldContainer[AlertSetting]
    def __init__(self, id: _Optional[int] = ..., title: _Optional[str] = ..., updated_at: _Optional[str] = ..., user: _Optional[int] = ..., alert_settings: _Optional[_Iterable[_Union[AlertSetting, _Mapping]]] = ...) -> None: ...

class AlertSettingsGroupRetrieveRequest(_message.Message):
    __slots__ = ("author_id", "group_id", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    group_id: int
    updated_at: str
    def __init__(self, author_id: _Optional[int] = ..., group_id: _Optional[int] = ..., updated_at: _Optional[str] = ...) -> None: ...
