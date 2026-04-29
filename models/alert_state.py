import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WidgetAlertState(BaseModel):
    current_alert_id: int | None = Field(None)
    start_viewing_at: datetime.datetime | None = Field(None)
    current_donation_id: int | None = Field(None)
    status: Literal["idle", "moderation", "viewing"] | None = Field(None)

    @model_validator(mode="after")
    def set_default_status(self):
        if self.status is None:
            self.status = "moderation" if self.current_alert_id is not None else "idle"
        return self
