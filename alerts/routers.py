import asyncio
import jwt

from fastapi import APIRouter, WebSocket, WebSocketException, status

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import check_widget_token, decode_custom_jwt, get_ws_messages_handler
from alerts.websocket import ws_manager


router = APIRouter()


@router.websocket("/ws/alerts/{widget_token}")
async def websocket_alert_endpoint(websocket: WebSocket, widget_token: str):
    try:
        widget_token_info = decode_custom_jwt(widget_token)
    except jwt.InvalidTokenError as e:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "invalid widget_token")

    if not await check_widget_token(widget_token_info):
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "invalid widget_token")

    await ws_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(widget_token_info.author_id)
    await ws_manager.listen(
        widget_token_info.author_id,
        websocket,
        get_ws_messages_handler(widget_token_info.author_id, exchange),
    )
