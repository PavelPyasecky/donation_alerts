from enum import Enum

from pydantic import BaseModel, Field

from models.alert import Alert, AlertStatus, BanWord
from models.campaign import Campaign
from models.alert import AlertSettingsGroup
from models.alert import SkipAlert
from models.donations import Donater, Donation
from models.settings import ModerationSettings, StatisticWidgetSettings
from models.top_donaters import DonationEvent
from models.videos import RabbitMQVideoStatus, Video, VideoControlCommand, VideoState, WidgetVideoSetting
from models.widget_status import WidgetStatus


class WidgetMessageTypes(Enum):
    event = "event"
    update = "update"


class ConnectedGroupsInfo(BaseModel):
    groups: list[AlertSettingsGroup]
    connected_groups_ids: list[int]


class WidgetMessage(BaseModel):
    type_: WidgetMessageTypes = Field(alias="type")
    action: str
    data: (
        Alert
        | Campaign
        | SkipAlert
        | AlertSettingsGroup
        | AlertStatus
        | WidgetStatus
        | list[Alert]
        | ConnectedGroupsInfo
        | BanWord
        | StatisticWidgetSettings
        | list[Donater]
        | DonationEvent
        | ModerationSettings
        | list[Donation]
        | WidgetVideoSetting
        | list[Video]
        | Video
        | RabbitMQVideoStatus
        | VideoControlCommand
        | VideoState
    )

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

    @classmethod
    def make_ban_words_message(cls, ban_words: BanWord):
        return cls(type=WidgetMessageTypes.update, action="ban_words", data=ban_words)

    @classmethod
    def make_connected_groups_info_message(cls, connected_groups_info: ConnectedGroupsInfo):
        return cls(type=WidgetMessageTypes.update, action="connected_groups_info", data=connected_groups_info)

    @classmethod
    def make_statistic_widget_settings_message(cls, statistic_widget_settings: StatisticWidgetSettings):
        return cls(type=WidgetMessageTypes.update, action="statistic_widget_settings", data=statistic_widget_settings)

    @classmethod
    def make_union_by_donor_names_list_message(cls, union_by_donor_names_list: list[Donater]):
        return cls(type=WidgetMessageTypes.update, action="union_by_donor_names_list", data=union_by_donor_names_list)

    @classmethod
    def make_moderation_settings_message(cls, moderation_settings: ModerationSettings):
        return cls(type=WidgetMessageTypes.update, action="moderation_settings", data=moderation_settings)

    @classmethod
    def make_last_donations_list_message(cls, last_donations_list: list[Donation]):
        return cls(type=WidgetMessageTypes.update, action="last_donations_list", data=last_donations_list)

    @classmethod
    def make_widget_video_settings_message(cls, widget_video_settings: WidgetVideoSetting):
        return cls(type=WidgetMessageTypes.update, action="widget_video_settings", data=widget_video_settings)

    @classmethod
    def make_widget_videos_message(cls, widget_videos: list[Video]):
        return cls(type=WidgetMessageTypes.update, action="widget_videos", data=widget_videos)
    
    @classmethod
    def make_donator_videos_message(cls, donator_videos: list[Video]):
        return cls(type=WidgetMessageTypes.update, action="donator_videos", data=donator_videos)

    @classmethod
    def make_video_state_message(cls, video_state: VideoState):
        return cls(type=WidgetMessageTypes.update, action="video_state", data=video_state)
