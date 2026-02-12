from fastapi import APIRouter, WebSocket
import jwt

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import decode_custom_jwt, get_ws_messages_handler
from alerts.websocket import ws_manager


router = APIRouter()


@router.websocket("/ws/alerts/{widget_token}")
async def websocket_alert_endpoint(websocket: WebSocket, widget_token: str):
    try:
        widget_token_info = decode_custom_jwt(widget_token)
    except jwt.InvalidTokenError as e:
        await websocket.close(400, f"invalid widget_token: {e}")
        return

    await ws_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(widget_token_info.author_id)
    await ws_manager.listen(widget_token_info.author_id, get_ws_messages_handler(author_id, exchange))
