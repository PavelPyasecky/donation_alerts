import settings_pb2 as _settings_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

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
    alert_settings: _containers.RepeatedCompositeFieldContainer[_settings_pb2.AlertSetting]
    def __init__(
        self,
        id: _Optional[int] = ...,
        title: _Optional[str] = ...,
        updated_at: _Optional[str] = ...,
        user: _Optional[int] = ...,
        alert_settings: _Optional[_Iterable[_Union[_settings_pb2.AlertSetting, _Mapping]]] = ...,
    ) -> None: ...

class AlertSettingsGroupRetrieveRequest(_message.Message):
    __slots__ = ("author_id", "group_id", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    group_id: int
    updated_at: str
    def __init__(
        self, author_id: _Optional[int] = ..., group_id: _Optional[int] = ..., updated_at: _Optional[str] = ...
    ) -> None: ...

class AlertSettingsGroupsListByAuthorIdRequest(_message.Message):
    __slots__ = ("author_id", "group_ids", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    group_ids: _containers.RepeatedScalarFieldContainer[int]
    updated_at: str
    def __init__(
        self,
        author_id: _Optional[int] = ...,
        group_ids: _Optional[_Iterable[int]] = ...,
        updated_at: _Optional[str] = ...,
    ) -> None: ...

class AlertSettingsGroupsListByAuthorIdResponse(_message.Message):
    __slots__ = ("groups",)
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[AlertSettingsGroup]
    def __init__(self, groups: _Optional[_Iterable[_Union[AlertSettingsGroup, _Mapping]]] = ...) -> None: ...
