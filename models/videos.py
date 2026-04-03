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
    command: Literal["pause", "resume", "skip"]
    video_id: int | None = Field(default=None)


class VideoState(BaseModel):
    video_id: int | None = Field(default=None)
    status: Literal["playing", "paused", "idle"] = Field(default="idle")
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


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
