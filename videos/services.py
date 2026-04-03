import datetime
import json

from aio_pika import Message
from aio_pika.abc import AbstractExchange

from configs.redis import get_user_state_redis_conn
from configs import config
from models.videos import RabbitMQVideoStatus, VideoControlCommand, VideoState
from models.widget_message import WidgetMessage, WidgetMessageTypes
from utils.task_manager import TaskManager
from videos.websocket import ws_videos_manager


def _video_state_key(author_id: int) -> str:
    return config.STREAMER_VIDEO_STATE_KEY.format(author_id=author_id)


async def get_video_state(author_id: int) -> VideoState:
    redis_conn = get_user_state_redis_conn()
    raw_state = await redis_conn.get(_video_state_key(author_id))
    if not raw_state:
        return VideoState()

    if isinstance(raw_state, bytes):
        raw_state = raw_state.decode()
    return VideoState(**json.loads(raw_state))


async def save_video_state(author_id: int, state: VideoState) -> None:
    redis_conn = get_user_state_redis_conn()
    await redis_conn.set(
        _video_state_key(author_id),
        state.model_dump_json(),
        ex=config.STREAMER_VIDEO_STATE_TTL_SECONDS,
    )


def _state_from_status(status: RabbitMQVideoStatus) -> VideoState:
    return VideoState(
        video_id=status.video_id,
        status=status.status,
        updated_at=status.viewed_at,
    )


def get_videos_ws_messages_handler(author_id: int, exchange: AbstractExchange):
    async def wrapper(message_data: dict):
        message = WidgetMessage(**message_data)
        match message.type_:
            case WidgetMessageTypes.update:
                match message.action:
                    case "video_status":
                        video_status = RabbitMQVideoStatus(
                            author_id=author_id,
                            **message.data.model_dump(exclude={"author_id"}),
                        )
                        await exchange.publish(
                            message=Message(body=video_status.model_dump_json().encode()),
                            routing_key=config.VIDEO_STATUS_QUEUE,
                        )
                        video_state = _state_from_status(video_status)
                        await save_video_state(author_id, video_state)
                        await ws_videos_manager.broadcast(
                            author_id,
                            WidgetMessage.make_video_state_message(video_state).model_dump(mode="json", by_alias=True),
                        )
                    case "video_control":
                        command = VideoControlCommand(**message.data.model_dump())
                        current_state = await get_video_state(author_id)
                        now = datetime.datetime.now(datetime.timezone.utc)
                        match command.command:
                            case "pause":
                                current_state.status = "paused"
                                if command.video_id is not None:
                                    current_state.video_id = command.video_id
                            case "resume":
                                current_state.status = "playing"
                                if command.video_id is not None:
                                    current_state.video_id = command.video_id
                            case "skip":
                                current_state.status = "idle"
                                current_state.video_id = None
                        current_state.updated_at = now
                        await save_video_state(author_id, current_state)
                        await ws_videos_manager.broadcast(
                            author_id,
                            WidgetMessage.make_video_state_message(current_state).model_dump(mode="json", by_alias=True),
                        )

    return wrapper


class VideoTaskManager(TaskManager):
    pass


video_task_manager = VideoTaskManager()
