from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RetrieveModerationSettingRequest(_message.Message):
    __slots__ = ("author_id", "updated_at")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    updated_at: str
    def __init__(self, author_id: _Optional[int] = ..., updated_at: _Optional[str] = ...) -> None: ...

class ModerationSetting(_message.Message):
    __slots__ = ("id", "is_active", "duration", "activation_amount", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    ACTIVATION_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: int
    is_active: bool
    duration: int
    activation_amount: str
    created_at: str
    updated_at: str
    def __init__(
        self,
        id: _Optional[int] = ...,
        is_active: bool = ...,
        duration: _Optional[int] = ...,
        activation_amount: _Optional[str] = ...,
        created_at: _Optional[str] = ...,
        updated_at: _Optional[str] = ...,
    ) -> None: ...
