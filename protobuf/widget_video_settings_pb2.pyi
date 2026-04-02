from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RetrieveWidgetVideoSettingsRequest(_message.Message):
    __slots__ = ("author_id", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    updated_at: str
    def __init__(self, author_id: _Optional[int] = ..., updated_at: _Optional[str] = ...) -> None: ...

class WidgetVideoSettings(_message.Message):
    __slots__ = ("id", "play_randomly", "show_video", "volume", "border_radius", "when_to_show_video_title", "last_viewed_widget_video")
    ID_FIELD_NUMBER: _ClassVar[int]
    PLAY_RANDOMLY_FIELD_NUMBER: _ClassVar[int]
    SHOW_VIDEO_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    BORDER_RADIUS_FIELD_NUMBER: _ClassVar[int]
    WHEN_TO_SHOW_VIDEO_TITLE_FIELD_NUMBER: _ClassVar[int]
    LAST_VIEWED_WIDGET_VIDEO_FIELD_NUMBER: _ClassVar[int]
    id: int
    play_randomly: bool
    show_video: bool
    volume: int
    border_radius: int
    when_to_show_video_title: str
    last_viewed_widget_video: LastViewedWidgetVideo
    def __init__(self, id: _Optional[int] = ..., play_randomly: bool = ..., show_video: bool = ..., volume: _Optional[int] = ..., border_radius: _Optional[int] = ..., when_to_show_video_title: _Optional[str] = ..., last_viewed_widget_video: _Optional[_Union[LastViewedWidgetVideo, _Mapping]] = ...) -> None: ...

class LastViewedWidgetVideo(_message.Message):
    __slots__ = ("video_id",)
    VIDEO_ID_FIELD_NUMBER: _ClassVar[int]
    video_id: int
    def __init__(self, video_id: _Optional[int] = ...) -> None: ...
