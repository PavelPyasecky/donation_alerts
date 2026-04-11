import datetime

from pydantic import BaseModel, Field


class WidgetAlertState(BaseModel):
    current_alert_id: int | None = Field(None)
    start_viewing_at: datetime.datetime | None = Field(None)
    current_donation_id: int | None = Field(None)
