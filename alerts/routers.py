from fastapi import APIRouter, WebSocket

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import check_widget_token, get_ws_messages_handler, send_alert_to_author_service
from alerts.websocket import ws_alerts_manager, ws_campaigns_manager
from configs import config
from alerts.grpc import campaign_grpc_client


router = APIRouter()


@router.websocket("/ws/alerts/{widget_token}")
async def websocket_alert_endpoint(websocket: WebSocket, widget_token: str):
    widget_token_info = await check_widget_token(widget_token)

    await ws_alerts_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(
        widget_token_info.author_id, config.ALERTS_EXCHANGE, status_queue=config.ALERT_STATUS_QUEUE
    )
    await ws_alerts_manager.listen(
        widget_token_info.author_id,
        websocket,
        get_ws_messages_handler(widget_token_info.author_id, exchange),
    )


@router.websocket("/ws/campaigns/{widget_token}")
async def websocket_campaigns_endpoint(websocket: WebSocket, widget_token: str):
    widget_token_info = await check_widget_token(widget_token)

    await ws_campaigns_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(
        widget_token_info.author_id, config.CAMPAIGNS_EXCHANGE, "campaigns_"
    )
    campaign = await campaign_grpc_client.get_campaign_by_author_id(widget_token_info.author_id)
    await ws_campaigns_manager.broadcast(
        widget_token_info.author_id, campaign.model_dump(mode="json") if campaign else {}
    )
    await ws_campaigns_manager.listen(widget_token_info.author_id, websocket)
