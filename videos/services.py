import datetime
from aio_pika import Message
from aio_pika.abc import AbstractExchange
from configs import config
from models.video_state import VideoControl, WidgetVideoQueue
from models.videos import RabbitMQVideoStatus
from models.widget_message import WidgetMessage, WidgetMessageTypes
from utils.task_manager import TaskManager
from videos.grpc import widget_videos_grpc_client, widget_video_settings_grpc_client
from videos.video_state import video_state_service


ZERO_DATETIME = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)


def get_videos_ws_messages_handler(author_id: int, exchange: AbstractExchange, ws_manager):
    async def wrapper(message_data: dict):
        message = WidgetMessage(**message_data)
        match message.type_:
            case WidgetMessageTypes.update:
                match message.action:
                    case "video_status":
                        await exchange.publish(
                            message=Message(body=message.data.model_dump_json().encode()),
                            routing_key=config.VIDEO_STATUS_QUEUE,
                        )
                    case "video_control":
                        command = VideoControl.model_validate(message.data.model_dump())

                        match command.command:
                            case "play":
                                if command.video_id is None or command.source is None:
                                    return
                                next_state = await video_state_service.play(author_id, command.video_id, command.source)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                            case "pause":
                                next_state = await video_state_service.pause(author_id)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                            case "idle":
                                next_state = await video_state_service.idle(author_id)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                            case "disable_video":
                                next_state = await video_state_service.disable_video(author_id)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                            case "enable_video":
                                next_state = await video_state_service.enable_video(author_id)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                            case "set_volume":
                                if command.volume is None:
                                    return
                                next_state = await video_state_service.set_volume(author_id, command.volume)
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                )
                                await widget_video_settings_grpc_client.set_volume(author_id, command.volume)
                            case "skip":
                                skipped_command = command.model_copy()
                                if command.source == "donators":
                                    current_state = await video_state_service.get_video_state(author_id)
                                    current_video_id = command.video_id or current_state.current_video_id
                                    if current_video_id is None:
                                        return
                                    skipped_command.video_id = current_video_id

                                    video_status = RabbitMQVideoStatus(
                                        author_id=author_id,
                                        video_id=current_video_id,
                                        viewed_at=datetime.datetime.now(datetime.timezone.utc),
                                    )
                                    await exchange.publish(
                                        message=Message(body=video_status.model_dump_json().encode()),
                                        routing_key=config.VIDEO_STATUS_QUEUE,
                                    )
                                else:
                                    widget_videos = await widget_videos_grpc_client.get_videos(author_id, ZERO_DATETIME)
                                    next_state, next_queue = await video_state_service.skip(
                                        author_id,
                                        original_videos=widget_videos or [],
                                        source=command.source,
                                    )
                                    await ws_manager.broadcast(
                                        author_id,
                                        WidgetMessage.make_video_state_message(next_state).model_dump(mode="json", by_alias=True),
                                    )
                                    if next_queue is not None:
                                        await ws_manager.broadcast(
                                            author_id,
                                            WidgetMessage.make_video_queue_message(next_queue).model_dump(
                                                mode="json", by_alias=True
                                            ),
                                        )
                                await ws_manager.broadcast(
                                    author_id,
                                    WidgetMessage(
                                        type=WidgetMessageTypes.update,
                                        action="video_control",
                                        data=skipped_command,
                                    ).model_dump(mode="json", by_alias=True),
                                )
                    case "video_queue":
                        requested_queue = WidgetVideoQueue.model_validate(message.data.model_dump())
                        widget_videos = await widget_videos_grpc_client.get_videos(author_id, ZERO_DATETIME)
                        next_queue = await video_state_service.reorder_video_queue(
                            author_id,
                            requested_queue=requested_queue,
                            original_videos=widget_videos or [],
                        )
                        if next_queue is not None:
                            await ws_manager.broadcast(
                                author_id,
                                WidgetMessage.make_video_queue_message(next_queue).model_dump(mode="json", by_alias=True),
                            )

    return wrapper


class VideoTaskManager(TaskManager):
    pass


video_task_manager = VideoTaskManager()
