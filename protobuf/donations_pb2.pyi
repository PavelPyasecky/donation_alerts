from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LastDonationsListRequest(_message.Message):
    __slots__ = ("author_id", "limit")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    limit: int
    def __init__(self, author_id: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class Donation(_message.Message):
    __slots__ = ("id", "donor_name", "amount", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    DONOR_NAME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: int
    donor_name: str
    amount: str
    created_at: str
    def __init__(self, id: _Optional[int] = ..., donor_name: _Optional[str] = ..., amount: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class LastDonationsListResponse(_message.Message):
    __slots__ = ("last_donations",)
    LAST_DONATIONS_FIELD_NUMBER: _ClassVar[int]
    last_donations: _containers.RepeatedCompositeFieldContainer[Donation]
    def __init__(self, last_donations: _Optional[_Iterable[_Union[Donation, _Mapping]]] = ...) -> None: ...

class UnionByDonorNamesListRequest(_message.Message):
    __slots__ = ("author_id", "start_time", "end_time", "limit")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    start_time: str
    end_time: str
    limit: int
    def __init__(self, author_id: _Optional[int] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class UnionByDonorNamesDonationsListResponse(_message.Message):
    __slots__ = ("union_by_donor_names_donations",)
    UNION_BY_DONOR_NAMES_DONATIONS_FIELD_NUMBER: _ClassVar[int]
    union_by_donor_names_donations: _containers.RepeatedCompositeFieldContainer[UnionByDonorNamesDonation]
    def __init__(self, union_by_donor_names_donations: _Optional[_Iterable[_Union[UnionByDonorNamesDonation, _Mapping]]] = ...) -> None: ...

class UnionByDonorNamesDonation(_message.Message):
    __slots__ = ("donor_name", "total_amount", "total_count", "last_created_at")
    DONOR_NAME_FIELD_NUMBER: _ClassVar[int]
    TOTAL_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    LAST_CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    donor_name: str
    total_amount: str
    total_count: int
    last_created_at: str
    def __init__(self, donor_name: _Optional[str] = ..., total_amount: _Optional[str] = ..., total_count: _Optional[int] = ..., last_created_at: _Optional[str] = ...) -> None: ...
