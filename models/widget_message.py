from enum import Enum

from pydantic import BaseModel, Field

from models.alert import Alert, AlertStatus
from models.campaign import Campaign
from models.alert import AlertSettingsGroup
from models.alert import SkipAlert
from models.widget_status import WidgetStatus


class WidgetMessageTypes(Enum):
    event = "event"
    update = "update"


class WidgetMessage(BaseModel):
    type_: WidgetMessageTypes = Field(alias="type")
    action: str
    data: Alert | Campaign | SkipAlert | AlertSettingsGroup | AlertStatus | WidgetStatus | list[Alert]

    @classmethod
    def make_alert_settings_group_message(cls, alert_settings_group: AlertSettingsGroup):
        return cls(
            type=WidgetMessageTypes.update,
            action="alert_settings",
            data=alert_settings_group,
        )

    @classmethod
    def make_campaign_message(cls, campaign: Campaign):
        return cls(type=WidgetMessageTypes.update, action="campaign", data=campaign)

    @classmethod
    def make_pending_alerts_message(cls, alerts: list[Alert]):
        return cls(type=WidgetMessageTypes.update, action="pending_alerts", data=alerts)
