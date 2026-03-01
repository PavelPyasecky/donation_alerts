import asyncio
import datetime
import json
import jwt
import logging

from aio_pika import Message
from aio_pika.abc import AbstractExchange, AbstractQueue
from fastapi import WebSocketDisconnect, WebSocketException, status

from alerts.websocket import WSManager, ws_alerts_manager, ws_campaigns_manager
from alerts.models import (
    Alert,
    AlertStatus,
    MessageTypes,
    RabbitMQAlertStatus,
    Statuses,
    WidgetTokenInfo,
    WidgetMessage,
)
from configs.redis import get_redis_conn
from configs import config


class ConsumerTasksManager:
    def __init__(self, ws_alerts_manager: WSManager, ws_campaigns_manager: WSManager):
        self.authors_tasks: dict[int, asyncio.Task] = {}
        self.ws_alerts_manager = ws_alerts_manager
        self.ws_campaigns_manager = ws_campaigns_manager
        self.lock = asyncio.Lock()

    async def start_queue_iter(self, manager_type: str, author_id: int, queue: AbstractQueue, exchange: AbstractExchange):
        ws_manager = self._get_current_manager(manager_type)
        async with self.lock:
            if author_id in self.authors_tasks:
                self.authors_tasks[author_id].cancel()
            task = asyncio.create_task(self._queue_iter(ws_manager, author_id, queue, exchange))
            self.authors_tasks[author_id] = task

    async def remove_task(self, author_id: int):
        async with self.lock:
            if author_id in self.authors_tasks:
                self.authors_tasks[author_id].cancel()
                self.authors_tasks.pop(author_id)
    
    def _get_current_manager(self, manager_type: str) -> WSManager:
        match manager_type:
            case config.ALERTS_EXCHANGE:
                return self.ws_alerts_manager
            case config.CAMPAIGNS_EXCHANGE:
                return self.ws_campaigns_manager
            case _:
                raise TypeError("Unknown WS manager type")

    async def _queue_iter(self, ws_manager: WSManager, author_id: int, queue: AbstractQueue, exchange: AbstractExchange):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    alert = Alert(**data)
                    if not ws_manager.is_author_connected(author_id):
                        await ws_manager.clear_disconnected(author_id)
                        await self.remove_task(author_id)
                        await message.nack()
                        return
                    asyncio.create_task(send_alert_to_author_service(ws_manager, alert, exchange))


consumer_tasks_manager = ConsumerTasksManager(ws_alerts_manager, ws_campaigns_manager)


async def send_alert_to_author_service(
    ws_manager: WSManager, alert: Alert, exchange: AbstractExchange, current_attemp: int = 1
) -> AlertStatus:
    try:
        await ws_manager.broadcast(alert.author_id, alert.model_dump(mode="json"))
    except WebSocketDisconnect as e:
        logging.error(f"Error when sending alert {alert.alert_id}: {e}")
        await asyncio.sleep(20)
        if current_attemp < 2:
            return await send_alert_to_author_service(alert, exchange, current_attemp + 1)
        else:
            status = AlertStatus(
                alert_id=alert.alert_id,
                status=Statuses.error,
                external_id=f"fastapi_alert_{alert.alert_id}",
                delivered_at=datetime.datetime.now(),
            )

            await exchange.publish(
                message=Message(body=status.model_dump_json().encode()),
                routing_key=config.ALERT_STATUS_QUEUE,
            )


def get_ws_messages_handler(author_id: int, exchange: AbstractExchange):
    async def wrapper(message_data: dict):
        message = WidgetMessage(**message_data)

        match message.type_:
            case MessageTypes.alert_status:
                alert_status = RabbitMQAlertStatus(author_id=author_id, **message.data.model_dump())
                await exchange.publish(
                    message=Message(body=alert_status.model_dump_json().encode()),
                    routing_key=config.ALERT_STATUS_QUEUE,
                )
            case MessageTypes.widget_status:
                if message.data.is_online:
                    redis_conn = get_redis_conn()
                    await redis_conn.setex(f"streamer:{author_id}:online", 60, 1)

    return wrapper


def decode_custom_jwt(token: str) -> WidgetTokenInfo:
    secret_key = config.WIDGET_TOKEN_SECRET
    algorithm = "HS256"

    payload = jwt.decode(token, secret_key, algorithms=[algorithm])

    return WidgetTokenInfo(**payload)


async def check_widget_token(widget_token: str) -> WidgetTokenInfo:
    try:
        token_info = decode_custom_jwt(widget_token)
    except jwt.InvalidTokenError as e:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "invalid widget_token")

    conn = get_redis_conn()

    cache_key = f"streamer:{token_info.author_id}:widget_control"
    control_uuid = (await conn.get(cache_key)).decode()

    if control_uuid is None or control_uuid != token_info.control_uuid:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "invalid widget_token")
    return token_info
