import asyncio
import logging

from fastapi import WebSocketException, status
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState


class WSManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, author_id: int, websocket: WebSocket):
        await websocket.accept()
        if websocket.client_state != WebSocketState.CONNECTED:
            logging.error(f"Websocket accept error: websocket status {websocket.client_state}")
            raise WebSocketException(
                status.WS_1006_ABNORMAL_CLOSURE, f"Websocket accept error: websocket status {websocket.client_state}"
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
                filter(lambda ws: ws.client_state == WebSocketState.CONNECTED, self.connections[author_id])
            )

    def is_author_connected(self, author_id: int) -> bool:
        if author_id not in self.connections:
            return False
        if not list(filter(lambda ws: ws.client_state == WebSocketState.CONNECTED, self.connections[author_id])):
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
            raise WebSocketException(status.WS_1002_PROTOCOL_ERROR, "incorrect message")


ws_manager = WSManager()
