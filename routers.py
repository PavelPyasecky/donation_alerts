import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketException,
)

from alerts.services import get_ws_messages_handler, alert_task_manager
from alerts.websocket import ws_alerts_manager
from campaigns.websocket import ws_campaigns_manager
from alerts.grpc import alert_settings_group_grpc_client, alerts_grpc_client
from campaigns.grpc import campaign_grpc_client
from configs import config
from models.widget_message import WidgetMessage
from models.widget_token import WidgetTokenInfo
from services.widgets import parse_widget_token
from utils.rabbitmq import rabbitmq

widgets_router = APIRouter(prefix="/ws")


@widgets_router.websocket("/alerts/")
async def websocket_alert_endpoint(
    websocket: WebSocket,
    group_id: int = None,
    widget_token_info: WidgetTokenInfo = Depends(parse_widget_token),
    get_pending_donations: bool = False,
):
    key = widget_token_info.author_id

    await ws_alerts_manager.connect(key, websocket)

    async def _stop_key_tasks():
        await alert_task_manager.stop_single_async_task((key, -1))

    ws_alerts_manager.register_on_empty(key, _stop_key_tasks)

    if group_id:
        alert_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
            widget_token_info.author_id,
            group_id,
            datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
        )
        if alert_settings_group is None:
            await ws_alerts_manager.disconnect(key, websocket)
            raise WebSocketException(status.WS_1003_UNSUPPORTED_DATA, "settings group not found")
        message = WidgetMessage.make_alert_settings_group_message(alert_settings_group)

        group_key = (key, group_id)
        await ws_alerts_manager.add_connection(group_key, websocket)
        await ws_alerts_manager.broadcast(group_key, message.model_dump(mode="json", by_alias=True))

        async def _stop_group_tasks():
            await alert_task_manager.stop_single_async_task(group_key)

        ws_alerts_manager.register_on_empty(group_key, _stop_group_tasks)

        await alert_task_manager.start_single_schedule_task(
            group_key,
            5,
            ws_alerts_manager.broadcast_alerts_group,
            group_key,
            widget_token_info.author_id,
            group_id,
            [alert_settings_group.updated_at],
        )

    if get_pending_donations:
        pending_donations = await alerts_grpc_client.get_pending_donations(widget_token_info.author_id)
        message = WidgetMessage.make_pending_alerts_message(pending_donations)
        await ws_alerts_manager.broadcast(group_key, message.model_dump(mode="json", by_alias=True))

    exchange, queue = await rabbitmq.declare_queue(config.ALERTS_EXCHANGE, str(key))
    exchange, statuses_queue = await rabbitmq.declare_queue(config.ALERTS_EXCHANGE, config.ALERT_STATUS_QUEUE)

    await alert_task_manager.start_single_async_task(
        (key, -1), rabbitmq.queue_iter, queue, ws_alerts_manager.on_rmq_message(key, widget_token_info.author_id)
    )

    await ws_alerts_manager.listen(
        key,
        websocket,
        get_ws_messages_handler(widget_token_info.author_id, exchange),
    )


@widgets_router.websocket("/campaigns/")
async def websocket_campaigns_endpoint(
    websocket: WebSocket,
    campaign_id: int,
    widget_token_info: WidgetTokenInfo = Depends(parse_widget_token),
):
    campaign = await campaign_grpc_client.get_campaign_by_id_author_id(widget_token_info.author_id, campaign_id)
    if not campaign or campaign.author_id != widget_token_info.author_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "campaign not found")

    await ws_campaigns_manager.connect(campaign_id, websocket)
    message = WidgetMessage.make_campaign_message(campaign)
    await ws_campaigns_manager.broadcast(campaign_id, message.model_dump(mode="json", by_alias=True))

    exchange, queue = await rabbitmq.declare_queue(config.CAMPAIGNS_EXCHANGE, f"campaigns_{campaign_id}")

    async def _stop_campaign_tasks():
        await alert_task_manager.stop_single_async_task((campaign_id, 1))

    ws_campaigns_manager.register_on_empty(campaign_id, _stop_campaign_tasks)

    await alert_task_manager.start_single_async_task(
        (campaign_id, 1),
        rabbitmq.queue_iter,
        queue,
        ws_campaigns_manager.on_rmq_message(campaign_id),
    )

    await ws_campaigns_manager.listen(campaign_id, websocket)
