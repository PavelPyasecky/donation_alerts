import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Video(BaseModel):
    id: int
    url: str
    created_at: datetime.datetime


class RabbitMQVideoStatus(BaseModel):
    author_id: int | None = Field(default=None)
    video_id: int | None = Field(default=None)
    viewed_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: Literal["playing", "paused", "idle"] = Field(default="playing")


class VideoControlCommand(BaseModel):
    command: Literal["pause", "resume", "skip", "disable", "enable", "set_volume"]
    video_id: int | None = Field(default=None)
    volume: int | None = Field(default=None, ge=0, le=100)


class VideoQueueUpdateCommand(BaseModel):
    video_ids: list[int] = Field(default_factory=list)
    version: int | None = Field(default=None, ge=0)


class VideoState(BaseModel):
    video_id: int | None = Field(default=None)
    status: Literal["playing", "paused", "idle"] = Field(default="idle")
    video_disabled: bool = Field(default=False)
    volume: int | None = Field(default=None, ge=0, le=100)
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class StoredVideoQueue(BaseModel):
    video_ids: list[int] = Field(default_factory=list)
    play_randomly: bool = Field(default=False)
    version: int = Field(default=0, ge=0)
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class VideoQueue(StoredVideoQueue):
    videos: list[Video] = Field(default_factory=list)


class LastViewedVideo(BaseModel):
    video_id: int | None = Field(None)


class WidgetVideoSetting(BaseModel):
    id: int
    play_randomly: bool = Field(False)
    show_video: bool = Field(False)
    volume: int = Field(0)
    border_radius: int = Field(0)
    when_to_show_video_title: str = Field(default="")
    font: str = Field(default="")
    font_color: str = Field(default="")
    font_style: str = Field(default="")
    font_size: int = Field(0)
    border_color: str = Field(default="")
    border_width: int = Field(0)
    last_viewed_widget_video: LastViewedVideo

    created_at: datetime.datetime
    updated_at: datetime.datetime
