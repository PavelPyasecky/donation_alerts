from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Campaign(_message.Message):
    __slots__ = ("id", "title", "description", "target_amount", "collected_amount", "progress_percentage", "is_active", "is_default", "created_at", "updated_at", "start_at", "end_at", "is_active_now")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TARGET_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    COLLECTED_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    START_AT_FIELD_NUMBER: _ClassVar[int]
    END_AT_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_NOW_FIELD_NUMBER: _ClassVar[int]
    id: int
    title: str
    description: str
    target_amount: str
    collected_amount: str
    progress_percentage: float
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str
    start_at: str
    end_at: str
    is_active_now: bool
    def __init__(self, id: _Optional[int] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., target_amount: _Optional[str] = ..., collected_amount: _Optional[str] = ..., progress_percentage: _Optional[float] = ..., is_active: bool = ..., is_default: bool = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ..., start_at: _Optional[str] = ..., end_at: _Optional[str] = ..., is_active_now: bool = ...) -> None: ...

class CampaignList(_message.Message):
    __slots__ = ("campaigns",)
    CAMPAIGNS_FIELD_NUMBER: _ClassVar[int]
    campaigns: _containers.RepeatedCompositeFieldContainer[Campaign]
    def __init__(self, campaigns: _Optional[_Iterable[_Union[Campaign, _Mapping]]] = ...) -> None: ...

class GetByAuthorIDRequest(_message.Message):
    __slots__ = ("author_id",)
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    def __init__(self, author_id: _Optional[int] = ...) -> None: ...

class GetByIDAuthorIDRequest(_message.Message):
    __slots__ = ("author_id", "campaign_id")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_ID_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    campaign_id: int
    def __init__(self, author_id: _Optional[int] = ..., campaign_id: _Optional[int] = ...) -> None: ...
