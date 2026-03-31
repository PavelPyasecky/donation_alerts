import logging

from aio_pika import Message
from aio_pika.abc import AbstractExchange

from models.alert import RabbitMQAlertStatus
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager

logger = logging.getLogger(__name__)


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

    return wrapper


async def mark_streamer_online(author_id: int):
    user_state_redis_conn = get_user_state_redis_conn()
    await user_state_redis_conn.set(config.STREAMER_ONLINE_KEY.format(author_id=author_id), 1)


async def mark_streamer_offline(author_id: int):
    user_state_redis_conn = get_user_state_redis_conn()
    await user_state_redis_conn.delete(config.STREAMER_ONLINE_KEY.format(author_id=author_id))


async def mark_streamer_group_connected(author_id: int, group_id: int) -> None:
    redis_conn = get_user_state_redis_conn()
    await redis_conn.sadd(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id), group_id)


async def mark_streamer_group_disconnected(author_id: int, group_id: int) -> None:
    redis_conn = get_user_state_redis_conn()
    await redis_conn.srem(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id), group_id)
    groups_count = await redis_conn.scard(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id))
    if groups_count == 0:
        await redis_conn.delete(config.STREAMER_ONLINE_KEY.format(author_id=author_id))


async def get_connected_groups(author_id: int) -> list[int]:
    redis_conn = get_user_state_redis_conn()
    groups = await redis_conn.smembers(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id))
    return sorted(int(group_id) for group_id in groups)


class AlertTaskManager(TaskManager):
    pass


alert_task_manager = AlertTaskManager()
