from aio_pika import Message
from aio_pika.abc import AbstractExchange

from models.alert import RabbitMQAlertStatus
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager


def get_ws_messages_handler(author_id: int, exchange: AbstractExchange):
    async def wrapper(message_data: dict):
        message = WidgetMessage(**message_data)

        match message.type_:
            case WidgetMessageTypes.update:
                match message.action:
                    case "alert_status":
                        alert_status = RabbitMQAlertStatus(author_id=author_id, **message.data.model_dump())
                        await exchange.publish(
                            message=Message(body=alert_status.model_dump_json().encode()),
                            routing_key=config.ALERT_STATUS_QUEUE,
                        )
                    case "widget_status":
                        if message.data.is_online:
                            redis_conn = get_user_state_redis_conn()
                            await redis_conn.setex(f"streamer:{author_id}:online", 60, 1)

    return wrapper


class AlertTaskManager(TaskManager):
    pass


alert_task_manager = AlertTaskManager()
