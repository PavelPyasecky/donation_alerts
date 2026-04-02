import datetime
from dataclasses import dataclass, field


@dataclass
class ConnectedGroupsPollState:
    connected_group_ids: list[int] = field(default_factory=list)
    updated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    )
