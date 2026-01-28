from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import get_status_publisher
from alerts.websocket import ws_manager


router = APIRouter()


@router.websocket("/ws/alerts/{author_id}")
async def websocket_alert_endpoint(websocket: WebSocket, author_id: int):
    await ws_manager.connect(author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(author_id)
    await ws_manager.listen(author_id, get_status_publisher(exchange))
