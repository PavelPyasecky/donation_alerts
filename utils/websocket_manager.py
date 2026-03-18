import asyncio
import logging

from fastapi import WebSocket, WebSocketException, status
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState


class WSManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.connections: dict[any, list[WebSocket]] = {}
    
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

    def start_schedule_task(self, interval_seconds: float, action: callable, *args, **kwargs) -> asyncio.Task:
        async def scheduler(*args, **kwargs):
            while True:
                result = await action(*args, **kwargs)
                if not result:
                    break
                asyncio.sleep(interval_seconds)

        return asyncio.create_task(scheduler(*args, **kwargs))
