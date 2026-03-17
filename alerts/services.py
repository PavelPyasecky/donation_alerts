import asyncio
import datetime
import json
import jwt
import logging

from aio_pika import Message
from aio_pika.abc import AbstractExchange, AbstractQueue
from fastapi import Request, WebSocketDisconnect, WebSocketException, status

from alerts.grpc import alert_settings_group_grpc_client
from alerts.websocket import WSManager, ws_alerts_manager
from models.alert import AlertStatus, RabbitMQAlertStatus
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager


class ConsumerTasksManager:
    def __init__(self, ws_alerts_manager: WSManager, ws_campaigns_manager: WSManager):
        self.authors_tasks: dict[int, asyncio.Task] = {}
        self.ws_alerts_manager = ws_alerts_manager
        self.ws_campaigns_manager = ws_campaigns_manager
        self.lock = asyncio.Lock()

    async def start_queue_iter(
        self, manager_type: str, author_id: int, queue: AbstractQueue, exchange: AbstractExchange
    ):
        async with self.lock:
            if author_id in self.authors_tasks:
                self.authors_tasks[author_id].cancel()
            task = asyncio.create_task(self._queue_iter(manager_type, author_id, queue, exchange))
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

    async def _queue_iter(self, manager_type: str, author_id: int, queue: AbstractQueue, exchange: AbstractExchange):
        ws_manager = self._get_current_manager(manager_type)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                    except Exception as e:
                        logging.error(f"Error when get message from rabbitmq: {e}")
                        continue
                    try:
                        message_model = RabbitMessage(**data)
                        match manager_type:
                            case config.ALERTS_EXCHANGE:
                                if not ws_manager.is_author_connected(author_id):
                                    await ws_manager.clear_disconnected(author_id)
                                    await self.remove_task(author_id)
                                    await message.nack()
                                    return
                                asyncio.create_task(
                                    send_message_to_author_service(
                                        ws_manager, message_model.data.author_id, message_model, exchange
                                    )
                                )
                            case config.CAMPAIGNS_EXCHANGE:
                                if not ws_manager.is_author_connected(author_id):
                                    await ws_manager.clear_disconnected(author_id)
                                    await self.remove_task(author_id)
                                    await message.nack()
                                    return
                                asyncio.create_task(
                                    send_message_to_author_service(
                                        ws_manager, message_model.data.id, message_model, exchange
                                    )
                                )
                    except Exception as e:
                        logging.error(f"Error when process message from rabbitmq: {e}")
                        continue


# consumer_tasks_manager = ConsumerTasksManager(ws_alerts_manager, ws_campaigns_manager)


async def send_message_to_author_service(
    ws_manager: WSManager, id_: int, message: WidgetMessage, exchange: AbstractExchange, current_attemp: int = 1
) -> AlertStatus:
    try:
        await ws_manager.broadcast(id_, message.model_dump(mode="json", by_alias=True))
    except WebSocketDisconnect as e:
        logging.error(f"Error when sending alert {id_}: {e}")
        await asyncio.sleep(20)
        if current_attemp < 2:
            return await send_message_to_author_service(ws_manager, id_, message, exchange, current_attemp + 1)
        else:
            if isinstance(message.data, Alert):
                status = AlertStatus(
                    alert_id=message.data.alert_id,
                    status=Statuses.error,
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
