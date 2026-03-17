import datetime

from pydantic import BaseModel


class WidgetTokenInfo(BaseModel):
    author_id: int
    created_at: datetime.datetime
    control_uuid: str
