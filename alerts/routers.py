from fastapi import APIRouter, WebSocket, WebSocketException, status

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.services import check_widget_token, get_ws_messages_handler
from alerts.websocket import ws_alerts_manager, ws_campaigns_manager
from configs import config
from alerts.grpc import campaign_grpc_client


router = APIRouter()


@router.websocket("/ws/alerts/{widget_token}")
async def websocket_alert_endpoint(websocket: WebSocket, widget_token: str, group_id: int):
    widget_token_info = await check_widget_token(widget_token)

    await ws_alerts_manager.connect(widget_token_info.author_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(
        widget_token_info.author_id, config.ALERTS_EXCHANGE, status_queue=config.ALERT_STATUS_QUEUE
    )

    get_send_alert_settings_task = await ws_alerts_manager.start_schedule_task(
        config.GET_ALET_SETTINGS_INTERVAL,
        ws_alerts_manager._get_and_send_alert_settings,
        author_id=widget_token_info.author_id,
        group_id=group_id,
    )

    await ws_alerts_manager.listen(
        widget_token_info.author_id,
        websocket,
        get_ws_messages_handler(widget_token_info.author_id, exchange),
    )


@router.websocket("/ws/campaigns/{campaign_id}/{widget_token}")
async def websocket_campaigns_endpoint(websocket: WebSocket, campaign_id: int, widget_token: str):
    widget_token_info = await check_widget_token(widget_token)
    campaign = await campaign_grpc_client.get_campaign_by_id_author_id(widget_token_info.author_id, campaign_id)
    if not campaign or campaign.author_id != widget_token_info.author_id:
        raise WebSocketException(status.WS_1003_UNSUPPORTED_DATA, "Campaign is not exists")

    await ws_campaigns_manager.connect(campaign_id, websocket)
    exchange = await rabbitmq_consumer.create_listener(campaign_id, config.CAMPAIGNS_EXCHANGE, "campaigns_")
    await ws_campaigns_manager.broadcast(campaign_id, campaign.model_dump(mode="json"))
    await ws_campaigns_manager.listen(campaign_id, websocket)
