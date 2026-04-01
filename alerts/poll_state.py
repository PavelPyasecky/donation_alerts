import datetime
from dataclasses import dataclass, field


@dataclass
class TimestampPollState:
    """Мутабельный курсор updated_at для периодических gRPC-опросов."""

    updated_at: datetime.datetime


@dataclass
class ConnectedGroupsPollState:
    """Состояние опроса connected groups + курсор для get_alert_settings_groups."""

    connected_group_ids: list[int] = field(default_factory=list)
    updated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    )
