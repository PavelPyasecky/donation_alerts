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
            return WebSocketException(
                status.WS_1006_ABNORMAL_CLOSURE, f"Websocket accept error: websocket status {websocket.client_state}"
            )
        async with self.lock():
            if author_id not in self.connections:
                self.connections[author_id] = []
            self.connections[author_id].append(WebSocket)

    async def clear_disconnected(self, author_id: int):
        if author_id not in self.connections:
            return
        self.connections[author_id] = list(
            filter(lambda ws: ws.client_state == WebSocketState.CONNECTED, self.connections[author_id])
        )
    
    def is_author_connected(self, author_id: int) -> bool:
        if author_id not in self.connections:
            return False
        if list(
            filter(lambda ws: ws.client_state == WebSocketState.CONNECTED, self.connections[author_id])
        ):
            return True
        return False
    
    async def send_to_author(self, author_id: int, data: dict):
        if author_id not in self.connections:
            logging.error(f"Author not in connections list")

    async def listen(self, auth)


ws_manager = WSManager()
