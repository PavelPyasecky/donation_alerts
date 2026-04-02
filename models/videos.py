import datetime
from pydantic import BaseModel, Field


class Video(BaseModel):
    id: int
    url: str
    created_at: datetime.datetime


class RabbitMQVideoStatus(BaseModel):
    author_id: int
    video_id: int
    viewed_at: datetime.datetime


class LastViewedVideo(BaseModel):
    video_id: int | None = Field(None)


class WidgetVideoSetting(BaseModel):
    id: int
    play_randomly: bool = Field(False)
    show_video: bool = Field(False)
    volume: int
    border_radius: int
    when_to_show_video_title: str
    last_viewed_video: LastViewedVideo

    created_at: datetime.datetime
    updated_at: datetime.datetime
