import datetime

from dataclasses import dataclass


@dataclass
class TimestampPollState:
    updated_at: datetime.datetime
