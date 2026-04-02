from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ListDonatorsVideosRequest(_message.Message):
    __slots__ = ("author_id", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    updated_at: str
    def __init__(self, author_id: _Optional[int] = ..., updated_at: _Optional[str] = ...) -> None: ...

class ListDonatorsVideosResponse(_message.Message):
    __slots__ = ("videos",)
    VIDEOS_FIELD_NUMBER: _ClassVar[int]
    videos: _containers.RepeatedCompositeFieldContainer[DonatorVideo]
    def __init__(self, videos: _Optional[_Iterable[_Union[DonatorVideo, _Mapping]]] = ...) -> None: ...

class DonatorVideo(_message.Message):
    __slots__ = ("id", "url", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: int
    url: str
    created_at: str
    def __init__(self, id: _Optional[int] = ..., url: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...
