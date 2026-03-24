from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetPendingDonationsRequest(_message.Message):
    __slots__ = ("author_id",)
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    author_id: int
    def __init__(self, author_id: _Optional[int] = ...) -> None: ...

class PendingDonationsResponse(_message.Message):
    __slots__ = ("pending_donations",)
    PENDING_DONATIONS_FIELD_NUMBER: _ClassVar[int]
    pending_donations: _containers.RepeatedCompositeFieldContainer[AlertData]
    def __init__(self, pending_donations: _Optional[_Iterable[_Union[AlertData, _Mapping]]] = ...) -> None: ...

class AlertData(_message.Message):
    __slots__ = ("id", "author_id", "donation_id", "amount", "message", "donor_name", "voice", "timestamp")
    ID_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    DONATION_ID_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DONOR_NAME_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    id: int
    author_id: int
    donation_id: int
    amount: str
    message: str
    donor_name: str
    voice: str
    timestamp: str
    def __init__(self, id: _Optional[int] = ..., author_id: _Optional[int] = ..., donation_id: _Optional[int] = ..., amount: _Optional[str] = ..., message: _Optional[str] = ..., donor_name: _Optional[str] = ..., voice: _Optional[str] = ..., timestamp: _Optional[str] = ...) -> None: ...
