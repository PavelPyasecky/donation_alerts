import datetime
import json
import random

from aio_pika import Message
from aio_pika.abc import AbstractExchange
from redis.exceptions import WatchError

from configs.redis import get_user_state_redis_conn
from configs import config
from models.videos import (
    RabbitMQVideoStatus,
    StoredVideoQueue,
    Video,
    VideoControlCommand,
    VideoQueue,
    VideoQueueUpdateCommand,
    VideoState,
)
from models.widget_message import WidgetMessage, WidgetMessageTypes
from utils.task_manager import TaskManager
from videos.grpc import widget_videos_grpc_client

REDIS_TRANSACTION_RETRIES = 5
ZERO_DATETIME = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)


def _video_state_key(author_id: int) -> str:
    return config.STREAMER_VIDEO_STATE_KEY.format(author_id=author_id)


def _video_queue_key(author_id: int) -> str:
    return config.STREAMER_VIDEO_QUEUE_KEY.format(author_id=author_id)


def _decode_json_model(raw_value, model_cls, default=None):
    if not raw_value:
        return default
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode()
    return model_cls(**json.loads(raw_value))


async def get_video_state(author_id: int) -> VideoState:
    redis_conn = get_user_state_redis_conn()
    return _decode_json_model(await redis_conn.get(_video_state_key(author_id)), VideoState, VideoState())


async def get_stored_video_queue(author_id: int) -> StoredVideoQueue | None:
    redis_conn = get_user_state_redis_conn()
    return _decode_json_model(await redis_conn.get(_video_queue_key(author_id)), StoredVideoQueue)


def _move_current_video_to_front(video_ids: list[int], current_video_id: int | None) -> list[int]:
    unique_ids = list(dict.fromkeys(video_ids))
    if current_video_id is None or current_video_id not in unique_ids:
        return unique_ids
    return [current_video_id, *(video_id for video_id in unique_ids if video_id != current_video_id)]


def _build_randomized_video_ids(original_video_ids: list[int], current_video_id: int | None) -> list[int]:
    ordered_ids = _move_current_video_to_front(original_video_ids, current_video_id)
    if not ordered_ids:
        return []

    head = ordered_ids[:1] if current_video_id in ordered_ids else []
    tail = ordered_ids[1:] if head else ordered_ids
    random.shuffle(tail)
    return [*head, *tail]


def _merge_queue_with_catalog(existing_video_ids: list[int], original_video_ids: list[int]) -> list[int]:
    original_video_ids = list(dict.fromkeys(original_video_ids))
    original_video_ids_set = set(original_video_ids)
    merged_video_ids = [video_id for video_id in existing_video_ids if video_id in original_video_ids_set]
    merged_video_ids.extend(video_id for video_id in original_video_ids if video_id not in merged_video_ids)
    return merged_video_ids


def _build_stored_video_queue(
    current_queue: StoredVideoQueue | None,
    video_ids: list[int],
    play_randomly: bool,
    updated_at: datetime.datetime,
) -> StoredVideoQueue:
    normalized_video_ids = list(dict.fromkeys(video_ids))
    if current_queue is not None:
        is_unchanged = (
            current_queue.video_ids == normalized_video_ids
            and current_queue.play_randomly == play_randomly
        )
        if is_unchanged:
            return current_queue
        version = current_queue.version + 1
    else:
        version = 1

    return StoredVideoQueue(
        video_ids=normalized_video_ids,
        play_randomly=play_randomly,
        version=version,
        updated_at=updated_at,
    )


def _build_queue_from_catalog(
    current_queue: StoredVideoQueue | None,
    widget_videos: list[Video],
    play_randomly: bool,
    current_video_id: int | None,
) -> StoredVideoQueue:
    original_video_ids = [video.id for video in widget_videos]
    now = datetime.datetime.now(datetime.timezone.utc)

    if current_queue is None or current_queue.play_randomly != play_randomly:
        if play_randomly:
            next_video_ids = _build_randomized_video_ids(original_video_ids, current_video_id)
        else:
            next_video_ids = _move_current_video_to_front(original_video_ids, current_video_id)
        return _build_stored_video_queue(current_queue, next_video_ids, play_randomly, now)

    next_video_ids = _merge_queue_with_catalog(current_queue.video_ids, original_video_ids)
    next_video_ids = _move_current_video_to_front(next_video_ids, current_video_id)
    return _build_stored_video_queue(current_queue, next_video_ids, play_randomly, now)


def _materialize_video_queue(queue: StoredVideoQueue | None, widget_videos: list[Video]) -> VideoQueue:
    if queue is None:
        return VideoQueue()

    videos_by_id = {video.id: video for video in widget_videos}
    ordered_videos = [videos_by_id[video_id] for video_id in queue.video_ids if video_id in videos_by_id]
    ordered_video_ids = [video.id for video in ordered_videos]
    return VideoQueue(
        video_ids=ordered_video_ids,
        videos=ordered_videos,
        play_randomly=queue.play_randomly,
        version=queue.version,
        updated_at=queue.updated_at,
    )


async def get_all_widget_videos(author_id: int) -> list[Video]:
    widget_videos = await widget_videos_grpc_client.get_videos(author_id, ZERO_DATETIME)
    return widget_videos or []


async def get_video_queue(author_id: int, widget_videos: list[Video] | None = None) -> VideoQueue:
    if widget_videos is None:
        widget_videos = await get_all_widget_videos(author_id)
    return _materialize_video_queue(await get_stored_video_queue(author_id), widget_videos)


async def _run_video_transaction(author_id: int, updater):
    redis_conn = get_user_state_redis_conn()
    state_key = _video_state_key(author_id)
    queue_key = _video_queue_key(author_id)

    for _ in range(REDIS_TRANSACTION_RETRIES):
        async with redis_conn.pipeline() as pipe:
            try:
                await pipe.watch(state_key, queue_key)
                current_state = _decode_json_model(await pipe.get(state_key), VideoState, VideoState())
                current_queue = _decode_json_model(await pipe.get(queue_key), StoredVideoQueue)

                next_state, next_queue, result = updater(current_state, current_queue)

                pipe.multi()
                if next_state is not None:
                    pipe.set(
                        state_key,
                        next_state.model_dump_json(),
                        ex=config.STREAMER_VIDEO_STATE_TTL_SECONDS,
                    )
                if next_queue is not None:
                    pipe.set(queue_key, next_queue.model_dump_json())
                await pipe.execute()
                return result
            except WatchError:
                continue

    raise RuntimeError(f"Failed to update video state for author_id={author_id}")


async def sync_video_queue_with_catalog(
    author_id: int,
    widget_videos: list[Video],
    play_randomly: bool,
    current_video_id: int | None = None,
) -> tuple[VideoQueue, bool]:
    def updater(current_state: VideoState, current_queue: StoredVideoQueue | None):
        effective_current_video_id = current_video_id if current_video_id is not None else current_state.video_id
        next_queue = _build_queue_from_catalog(current_queue, widget_videos, play_randomly, effective_current_video_id)
        payload = _materialize_video_queue(next_queue, widget_videos)
        queue_changed = current_queue != next_queue
        return current_state, next_queue, (payload, queue_changed)

    return await _run_video_transaction(author_id, updater)


def _move_queue_to_current_video(
    current_queue: StoredVideoQueue | None,
    current_video_id: int | None,
) -> StoredVideoQueue | None:
    if current_queue is None:
        return None
    return _build_stored_video_queue(
        current_queue,
        _move_current_video_to_front(current_queue.video_ids, current_video_id),
        current_queue.play_randomly,
        datetime.datetime.now(datetime.timezone.utc),
    )


async def apply_video_status(author_id: int, video_status: RabbitMQVideoStatus) -> tuple[VideoState, bool]:
    def updater(current_state: VideoState, current_queue: StoredVideoQueue | None):
        next_state = current_state.model_copy(
            update={
                "video_id": video_status.video_id,
                "status": video_status.status,
                "updated_at": video_status.viewed_at,
            }
        )
        next_queue = _move_queue_to_current_video(current_queue, next_state.video_id)
        queue_changed = current_queue != next_queue
        return next_state, next_queue, (next_state, queue_changed)

    return await _run_video_transaction(author_id, updater)


async def apply_video_control(author_id: int, command: VideoControlCommand) -> tuple[VideoState, bool]:
    def updater(current_state: VideoState, current_queue: StoredVideoQueue | None):
        next_state = current_state.model_copy()
        now = datetime.datetime.now(datetime.timezone.utc)

        match command.command:
            case "pause":
                next_state.status = "paused"
                if command.video_id is not None:
                    next_state.video_id = command.video_id
            case "resume":
                next_state.status = "playing"
                if command.video_id is not None:
                    next_state.video_id = command.video_id
            case "skip":
                next_state.status = "idle"
                next_state.video_id = None
            case "disable":
                next_state.video_disabled = True
                next_state.status = "idle"
                next_state.video_id = None
            case "enable":
                next_state.video_disabled = False
            case "set_volume":
                if command.volume is not None:
                    next_state.volume = command.volume

        next_state.updated_at = now
        next_queue = _move_queue_to_current_video(current_queue, next_state.video_id)
        queue_changed = current_queue != next_queue
        return next_state, next_queue, (next_state, queue_changed)

    return await _run_video_transaction(author_id, updater)


async def reorder_video_queue(author_id: int, command: VideoQueueUpdateCommand) -> bool:
    def updater(current_state: VideoState, current_queue: StoredVideoQueue | None):
        if current_queue is None:
            return current_state, current_queue, False

        if command.version is not None and command.version != current_queue.version:
            return current_state, current_queue, False

        normalized_video_ids = list(dict.fromkeys(command.video_ids))
        current_video_ids = current_queue.video_ids
        if (
            len(normalized_video_ids) != len(current_video_ids)
            or set(normalized_video_ids) != set(current_video_ids)
        ):
            return current_state, current_queue, False

        next_queue = _build_stored_video_queue(
            current_queue,
            _move_current_video_to_front(normalized_video_ids, current_state.video_id),
            current_queue.play_randomly,
            datetime.datetime.now(datetime.timezone.utc),
        )
        return current_state, next_queue, current_queue != next_queue

    return await _run_video_transaction(author_id, updater)


def get_videos_ws_messages_handler(author_id: int, exchange: AbstractExchange, ws_manager):
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
                        video_state, queue_changed = await apply_video_status(author_id, video_status)
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage.make_video_state_message(video_state).model_dump(mode="json", by_alias=True),
                        )
                        if queue_changed:
                            video_queue = await get_video_queue(author_id)
                            await ws_manager.broadcast(
                                author_id,
                                WidgetMessage.make_video_queue_message(video_queue).model_dump(mode="json", by_alias=True),
                            )
                    case "video_control":
                        command = VideoControlCommand(**message.data.model_dump())
                        current_state, queue_changed = await apply_video_control(author_id, command)
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage.make_video_state_message(current_state).model_dump(mode="json", by_alias=True),
                        )
                        if queue_changed:
                            video_queue = await get_video_queue(author_id)
                            await ws_manager.broadcast(
                                author_id,
                                WidgetMessage.make_video_queue_message(video_queue).model_dump(mode="json", by_alias=True),
                            )
                    case "video_queue":
                        command = VideoQueueUpdateCommand(**message.data.model_dump())
                        if await reorder_video_queue(author_id, command):
                            video_queue = await get_video_queue(author_id)
                            await ws_manager.broadcast(
                                author_id,
                                WidgetMessage.make_video_queue_message(video_queue).model_dump(mode="json", by_alias=True),
                            )

    return wrapper


class VideoTaskManager(TaskManager):
    pass


video_task_manager = VideoTaskManager()
