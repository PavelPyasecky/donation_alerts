import datetime
from aio_pika import Message
from aio_pika.abc import AbstractExchange
from configs import config
from models.videos import RabbitMQVideoStatus
from models.widget_message import WidgetMessage, WidgetMessageTypes
from utils.task_manager import TaskManager


def get_videos_ws_messages_handler(author_id: int, exchange: AbstractExchange):
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

    return wrapper


class VideoTaskManager(TaskManager):
    pass


video_task_manager = VideoTaskManager()
