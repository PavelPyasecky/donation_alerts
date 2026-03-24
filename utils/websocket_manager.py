import asyncio
import logging

from fastapi import WebSocket, WebSocketException, status
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState


class WSManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.connections: dict[any, list[WebSocket]] = {}
        self._on_empty_callbacks: dict[any, list[callable]] = {}
        self._cleanup_task: asyncio.Task | None = None
        self.start_cleanup_loop(2)
    
    async def add_connection(self, key: any, websocket: WebSocket):
        async with self.lock:
            if key not in self.connections:
                self.connections[key] = []
            self.connections[key].append(websocket)

    async def connect(self, key: any, websocket: WebSocket):
        await websocket.accept()
        if websocket.client_state != WebSocketState.CONNECTED:
            logging.error(f"Websocket accept error: websocket status {websocket.client_state}")
            raise WebSocketException(
                status.WS_1006_ABNORMAL_CLOSURE,
                f"Websocket accept error: websocket status {websocket.client_state}",
            )
        await self.add_connection(key, websocket)
        logging.info(f"WS connection {key} connected")

    async def disconnect(self, key: any, websocket: WebSocket):
        async with self.lock:
            if key in self.connections:
                try:
                    self.connections[key].remove(websocket)
                    await websocket.close()
                except ValueError:
                    pass

                if not self.connections[key]:
                    del self.connections[key]
                    logging.info(f"WS connection {key} fully disconnected")
                    await self._run_on_empty(key)
                else:
                    logging.info(
                        f"WS connection  {key} partially disconnected. Remaining: {len(self.connections[key])}"
                    )

    async def clear_disconnected(self, key: any):
        if key not in self.connections:
            return
        async with self.lock:
            self.connections[key] = list(
                filter(
                    lambda ws: ws.client_state == WebSocketState.CONNECTED,
                    self.connections[key],
                )
            )

    async def cleanup_disconnected_all(self) -> None:
        async with self.lock:
            disconnected_keys: list[any] = []
            for key, sockets in list(self.connections.items()):
                connected = []
                for ws in sockets:
                    if ws.client_state == WebSocketState.CONNECTED:
                        connected.append(ws)
                    else:
                        try:
                            await ws.close()
                        except RuntimeError:
                            pass
                if connected:
                    self.connections[key] = connected
                else:
                    disconnected_keys.append(key)
                    del self.connections[key]
            if not disconnected_keys:
                return

        for key in disconnected_keys:
            await self._run_on_empty(key)

    def is_author_connected(self, key: any) -> bool:
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

    def register_on_empty(self, key: any, callback: callable) -> None:
        if key not in self._on_empty_callbacks:
            self._on_empty_callbacks[key] = []
        self._on_empty_callbacks[key].append(callback)

    async def broadcast(self, key: any, data: dict):
        if not self.is_author_connected(key):
            logging.error(f"WS connection {key} not in connections list")
            return

        await self.clear_disconnected(key)

        async with self.lock:
            websockets = list(self.connections.get(key, []))

        async def _safe_send(ws: WebSocket):
            try:
                await ws.send_json(data)
            except (WebSocketDisconnect, RuntimeError) as e:
                logging.warning(f"Error sending to WS connection {key}: {e!r}. " "Removing websocket from connections.")
                await self.disconnect(key, ws)

        if not websockets:
            return

        await asyncio.gather(*(_safe_send(ws) for ws in websockets), return_exceptions=True)

    async def listen(self, key: any, websocket: WebSocket, on_message: callable = None):
        try:
            while True:
                data = await websocket.receive_json()
                if on_message:
                    await on_message(data)
        except WebSocketDisconnect:
            logging.error(f"Websocket {key} disconnected")
            await self.clear_disconnected(key)
        except Exception as e:
            logging.error(f"Unknown exception when received message {e}", exc_info=True)
        finally:
            await self.disconnect(key, websocket)

    async def _run_on_empty(self, key: any) -> None:
        callbacks = self._on_empty_callbacks.pop(key, [])
        if not callbacks:
            return
        for callback in callbacks:
            try:
                await callback()
            except Exception:
                logging.exception(f"Error in on-empty callback for key {key}")

    def start_cleanup_loop(self, interval_seconds: float = 30.0) -> asyncio.Task:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return self._cleanup_task

        async def _loop():
            while True:
                await asyncio.sleep(interval_seconds)
                await self.cleanup_disconnected_all()

        self._cleanup_task = asyncio.create_task(_loop())
        return self._cleanup_task
