import asyncio

import logging
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[int, WebSocket] = {}
        self.lock = asyncio.Lock()


    async def connect(self, author_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.connections[author_id] = websocket
    

    async def listen(self, author_id: int, on_message: callable = None):
        if author_id not in self.connections:
            return
        
        websocket = self.connections[author_id]
        while True:
            try:
                data = await websocket.receive_json()
                if on_message:
                    await on_message(data)
            except (WebSocketDisconnect, RuntimeError) as e:
                logging.error(f"Error when try to listen websocat {author_id}: {e}")
                await self.disconnect(author_id)

    async def disconnect(self, author_id: int):
        if not self.connections[author_id]:
            logging.warning(f"Ws connection to author {author_id} not exists")
            return
        if self.connections[author_id].client_state != WebSocketState.DISCONNECTED:
            await self.connections[author_id].close()
        async with self.lock:
            if author_id in self.connections:
                del self.connections[author_id]

    async def send_to_author(self, author_id: int, data: dict):
        if author_id not in self.connections:
            logging.error("Author not in connections")
            return
        try:
            await self.connections[author_id].send_json(data)
        except WebSocketDisconnect:
            await self.disconnect(author_id)
            raise WebSocketDisconnect
        

ws_manager = WebSocketManager()
