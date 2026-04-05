import datetime

from typing import Literal
from pydantic import BaseModel, Field

from models.videos import Video


class WidgetVideoState(BaseModel):
    current_video_id: int | None = Field(None)
    video_source: Literal["widget", "donators"] | None = Field(None)
    status: Literal["playing", "paused", "idle"] = Field("idle")
    video_disabled: bool = Field(False)
    volume: int = Field(0, ge=0, le=100)
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class VideoControl(BaseModel):
    command: Literal["play", "pause", "skip", "disable_video", "enable_video", "set_volume"]
    video_id: int | None = Field(None)
    source: Literal["widget", "donators"] | None = Field(None)
    volume: int | None = Field(None, ge=0, le=100)


class StoredWidgetVideoQueue(BaseModel):
    original_video_ids: list[int] = Field(default_factory=list)
    video_ids: list[int] = Field(default_factory=list)
    play_randomly: bool = Field(False)
    version: int = Field(0, ge=0)
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class WidgetVideoQueue(StoredWidgetVideoQueue):
    videos: list[Video] = Field(default_factory=list)
