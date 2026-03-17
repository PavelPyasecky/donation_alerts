import asyncio
import datetime
import json
import logging

from aio_pika.abc import AbstractIncomingMessage
from fastapi import WebSocketException, status
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from alerts.grpc import alert_settings_group_grpc_client
from alerts.models import RabbitMessage, RabbitMessageTypes
from models.widget_message import WidgetMessage
from utils.websocket_manager import WSManager


REDIS_ALERT_SETTING_LAST_UPDATED_AT_KEY = "alert_setting"


def _connection_key(author_id: int, group_id: int) -> tuple[int, int]:
    return (author_id, group_id)


class OLDWSManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, author_id: int, websocket: WebSocket):
        await websocket.accept()
        if websocket.client_state != WebSocketState.CONNECTED:
            logging.error(f"Websocket accept error: websocket status {websocket.client_state}")
            raise WebSocketException(
                status.WS_1006_ABNORMAL_CLOSURE,
                f"Websocket accept error: websocket status {websocket.client_state}",
            )
        async with self.lock:
            if author_id not in self.connections:
                self.connections[author_id] = []
            self.connections[author_id].append(websocket)
        logging.info(f"User {author_id} connected")

    async def disconnect(self, author_id: int, websocket: WebSocket):
        async with self.lock:
            if author_id in self.connections:
                try:
                    self.connections[author_id].remove(websocket)
                    await websocket.close()
                except ValueError:
                    pass

                if not self.connections[author_id]:
                    del self.connections[author_id]
                    logging.info(f"Author {author_id} fully disconnected")
                else:
                    logging.info(
                        f"Author {author_id} partially disconnected. Remaining: {len(self.connections[author_id])}"
                    )

    async def clear_disconnected(self, author_id: int):
        if author_id not in self.connections:
            return
        async with self.lock:
            self.connections[author_id] = list(
                filter(
                    lambda ws: ws.client_state == WebSocketState.CONNECTED,
                    self.connections[author_id],
                )
            )

    def is_author_connected(self, author_id: int) -> bool:
        if author_id not in self.connections:
            return False
        if not list(
            filter(
                lambda ws: ws.client_state == WebSocketState.CONNECTED,
                self.connections[author_id],
            )
        ):
            return False
        return True

    async def broadcast(self, author_id: int, data: dict):
        if not self.is_author_connected(author_id):
            logging.error(f"Author not in connections list")
            return
        await self.clear_disconnected(author_id)

        async with self.lock:
            tasks = []

            for ws in self.connections[author_id]:
                tasks.append(ws.send_json(data))

        await asyncio.gather(*tasks, return_exceptions=False)

    async def listen(self, author_id: int, websocket: WebSocket, on_message: callable = None):
        try:
            while True:
                data = await websocket.receive_json()
                if on_message:
                    await on_message(data)
        except WebSocketDisconnect:
            logging.error(f"Websocket disconnected for author {author_id}")
            await self.clear_disconnected(author_id)
        except Exception as e:
            logging.error(f"Unknown exception when received message {e}", exc_info=True)
        finally:
            await self.disconnect(author_id, websocket)

    async def start_schedule_task(self, interval_seconds: int, action: callable, **kwargs):
        return asyncio.create_task(action(interval_seconds=interval_seconds, **kwargs))


class OLDAlertsWSManager(OLDWSManager):
    """WSManager for alerts: one monitoring task per (author_id, group_id)."""

    def __init__(self):
        super().__init__()
        self.connections: dict[tuple[int, int], list[WebSocket]] = {}
        self._alert_settings_tasks: dict[tuple[int, int], asyncio.Task] = {}

    async def connect(self, author_id: int, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if websocket.client_state != WebSocketState.CONNECTED:
            logging.error(f"Websocket accept error: websocket status {websocket.client_state}")
            raise WebSocketException(
                status.WS_1006_ABNORMAL_CLOSURE,
                f"Websocket accept error: websocket status {websocket.client_state}",
            )
        key = _connection_key(author_id, group_id)
        async with self.lock:
            if key not in self.connections:
                self.connections[key] = []
            self.connections[key].append(websocket)
        logging.info(f"User {author_id} connected (group_id={group_id})")

    async def disconnect(self, author_id: int, websocket: WebSocket, group_id: int):
        key = _connection_key(author_id, group_id)
        async with self.lock:
            if key not in self.connections:
                return
            try:
                self.connections[key].remove(websocket)
                await websocket.close()
            except ValueError:
                pass

            if not self.connections[key]:
                del self.connections[key]
                if key in self._alert_settings_tasks:
                    task = self._alert_settings_tasks.pop(key)
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    logging.info(f"Author {author_id} group {group_id}: task stopped, fully disconnected")
                else:
                    logging.info(f"Author {author_id} group {group_id} fully disconnected")
            else:
                logging.info(
                    f"Author {author_id} group {group_id} partially disconnected. "
                    f"Remaining: {len(self.connections[key])}"
                )

    async def clear_disconnected(self, author_id: int, group_id: int):
        key = _connection_key(author_id, group_id)
        if key not in self.connections:
            return
        async with self.lock:
            self.connections[key] = list(
                filter(
                    lambda ws: ws.client_state == WebSocketState.CONNECTED,
                    self.connections[key],
                )
            )

    def is_author_connected(self, author_id: int, group_id: int | None = None) -> bool:
        if group_id is not None:
            key = _connection_key(author_id, group_id)
            if key not in self.connections:
                return False
            if not list(
                filter(
                    lambda ws: ws.client_state == WebSocketState.CONNECTED,
                    self.connections[key],
                )
            ):
                return False
            return True
        return any(
            self.is_author_connected(author_id, gid) for (aid, gid) in self.connections.keys() if aid == author_id
        )

    async def broadcast(self, author_id: int, data: dict, group_id: int | None = None):
        if group_id is None:
            if not self.is_author_connected(author_id):
                logging.error("Author not in connections list")
                return
            tasks: list[asyncio.Task | asyncio.Future] = []
            keys = [(aid, gid) for (aid, gid) in self.connections.keys() if aid == author_id]
            for _, gid in keys:
                await self.clear_disconnected(author_id, gid)
                key = _connection_key(author_id, gid)
                async with self.lock:
                    if key not in self.connections:
                        continue
                    tasks.extend(ws.send_json(data) for ws in self.connections[key])
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=False)
            return

        if not self.is_author_connected(author_id, group_id):
            logging.error("Author not in connections list for this group")
            return
        await self.clear_disconnected(author_id, group_id)
        key = _connection_key(author_id, group_id)
        async with self.lock:
            if key not in self.connections:
                return
            tasks = [ws.send_json(data) for ws in self.connections[key]]
        await asyncio.gather(*tasks, return_exceptions=False)

    async def listen(
        self,
        author_id: int,
        websocket: WebSocket,
        group_id: int,
        on_message: callable = None,
    ):
        try:
            while True:
                data = await websocket.receive_json()
                if on_message:
                    await on_message(data)
        except WebSocketDisconnect:
            logging.error(f"Websocket disconnected for author {author_id} group {group_id}")
            await self.clear_disconnected(author_id, group_id)
        except Exception as e:
            logging.error(f"Unknown exception when received message {e}", exc_info=True)
        finally:
            await self.disconnect(author_id, websocket, group_id)

    async def ensure_alert_settings_task(
        self, author_id: int, group_id: int, interval_seconds: int, initial_updated_at: datetime.datetime
    ):
        key = _connection_key(author_id, group_id)
        async with self.lock:
            if key in self._alert_settings_tasks:
                task = self._alert_settings_tasks[key]
                if not task.done():
                    return
                del self._alert_settings_tasks[key]
            task = asyncio.create_task(
                self._get_and_send_alert_settings(
                    interval_seconds=interval_seconds,
                    author_id=author_id,
                    group_id=group_id,
                    initial_updated_at=initial_updated_at,
                )
            )
            self._alert_settings_tasks[key] = task

    async def send_current_alert_settings(self, author_id: int, group_id: int):
        if not self.is_author_connected(author_id, group_id):
            return
        updated_at = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
        alerts_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
            author_id, group_id, updated_at
        )
        if alerts_settings_group is None:
            return
        message = RabbitMessage(
            type=RabbitMessageTypes.update,
            action="alert_settings",
            data=alerts_settings_group,
        )
        await self.broadcast(
            author_id,
            message.model_dump(mode="json", by_alias=True),
            group_id,
        )

        return alerts_settings_group

    async def _get_and_send_alert_settings(
        self, interval_seconds: int, author_id: int, group_id: int, initial_updated_at: datetime.datetime
    ):
        updated_at = initial_updated_at

        while True:
            if not self.is_author_connected(author_id, group_id):
                break

            alerts_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
                author_id, group_id, updated_at
            )

            if alerts_settings_group is None:
                await asyncio.sleep(interval_seconds)
                continue
            updated_at = alerts_settings_group.updated_at

            message = RabbitMessage(
                type=RabbitMessageTypes.update,
                action="alert_settings",
                data=alerts_settings_group,
            )

            await self.broadcast(
                author_id,
                message.model_dump(mode="json", by_alias=True),
                group_id,
            )
            await asyncio.sleep(interval_seconds)


# ws_alerts_manager = AlertsWSManager()
# ws_campaigns_manager = WSManager()


class AlertsWSManager(WSManager):
    async def broadcast_alerts_group(
        self, ws_key: any, author_id: int, group_id: int, updated_at: list[datetime.datetime]
    ):
        if not self.is_author_connected(ws_key):
            return False

        alert_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
            author_id, group_id, updated_at[0]
        )
        if alert_settings_group is None:
            return True

        updated_at[0] = alert_settings_group.updated_at[0]

        message = WidgetMessage.make_alert_settings_group_message(alert_settings_group)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True
    
    def on_rmq_message(self, ws_key: any):
        async def _on_rmq_message(message: AbstractIncomingMessage):
            async with message.process():
                if not self.is_author_connected(ws_key):
                    await message.nack(requeue=True)
                    return False
                data = json.loads(message.body.decode())
                message_model = WidgetMessage(**data)
                await self.broadcast(ws_key, message_model.model_dump(mode="json", by_alias=True))
                return True

        return _on_rmq_message
ws_alerts_manager = AlertsWSManager()
