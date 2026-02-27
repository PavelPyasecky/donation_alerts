from fastapi import APIRouter, WebSocket

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import check_widget_token, get_ws_messages_handler
from alerts.websocket import ws_alerts_manager, ws_campaigns_manager
from configs import config


router = APIRouter()


@router.websocket("/ws/alerts/{widget_token}")
async def websocket_alert_endpoint(websocket: WebSocket, widget_token: str):
    widget_token_info = await check_widget_token(widget_token)

    await ws_alerts_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(
        widget_token_info.author_id, config.ALERTS_EXCHANGE, config.ALERT_STATUS_QUEUE
    )
    await ws_alerts_manager.listen(
        widget_token_info.author_id,
        websocket,
        get_ws_messages_handler(widget_token_info.author_id, exchange),
    )


@router.websocket("ws/campaigns/{widget_token}")
async def websocket_campaigns_endpoint(websocket: WebSocket, widget_token: str):
    widget_token_info = await check_widget_token(widget_token)

    await ws_campaigns_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(
        widget_token_info.author_id, config.CAMPAIGNS_EXCHANGE, "campaigns_"
    )
    await ws_campaigns_manager.broadcast(widget_token_info.author_id, {})
    await ws_campaigns_manager.listen(widget_token_info.author_id, websocket)
