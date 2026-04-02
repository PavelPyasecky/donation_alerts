import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketException,
)

from alerts.poll_state import ConnectedGroupsPollState
from utils.poll_states import TimestampPollState
from alerts.services import get_ws_messages_handler, alert_task_manager
from alerts.websocket import ws_alerts_manager
from campaigns.services import campaign_task_manager
from campaigns.websocket import ws_campaigns_manager
from alerts.grpc import (
    alert_settings_group_grpc_client,
    alerts_grpc_client,
    ban_words_grpc_client,
    moderation_settings_grpc_client,
)
from campaigns.grpc import campaign_grpc_client
from configs import config
from models.widget_message import WidgetMessage
from models.widget_token import WidgetTokenInfo
from services.widgets import parse_widget_token
from top_donaters.grpc import donations_grpc_client, top_donaters_grpc_client
from top_donaters.services import top_donaters_task_manager
from top_donaters.websocket import ws_top_donaters_manager
from utils.rabbitmq import rabbitmq
from videos.grpc import widget_video_settings_grpc_client, widget_videos_grpc_client
from videos.services import get_videos_ws_messages_handler, video_task_manager
from videos.websocket import ws_videos_manager

widgets_router = APIRouter(prefix="/ws")


@widgets_router.websocket("/alerts/")
async def websocket_alert_endpoint(
    websocket: WebSocket,
    group_id: int = None,
    widget_token_info: WidgetTokenInfo = Depends(parse_widget_token),
    get_pending_donations: bool = False,
    get_ban_words: bool = False,
    get_moderation_settings: bool = False,
    statistic_widget_setting_id: int = None,
    get_connected_groups_info: bool = False,
):
    key = widget_token_info.author_id

    await ws_alerts_manager.connect(key, websocket)

    async def _stop_key_tasks():
        await alert_task_manager.stop_single_async_task((key, -1))
        await alert_task_manager.stop_single_async_task((key, "connected_groups_info"))

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
        await ws_alerts_manager.mark_group_widget_connected(widget_token_info.author_id, group_id)
        await websocket.send_json(message.model_dump(mode="json", by_alias=True))

        async def _stop_group_tasks():
            await alert_task_manager.stop_single_async_task(group_key)
            await ws_alerts_manager.mark_group_widget_disconnected(widget_token_info.author_id, group_id)

        ws_alerts_manager.register_on_empty(group_key, _stop_group_tasks)

        await alert_task_manager.start_single_schedule_task(
            group_key,
            config.CHECK_NEW_ALET_SETTINGS_INTERVAL,
            ws_alerts_manager.broadcast_alerts_group,
            group_key,
            widget_token_info.author_id,
            group_id,
            TimestampPollState(updated_at=alert_settings_group.updated_at),
        )

    if get_ban_words:
        ban_words_updated_at = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
        ban_words = await ban_words_grpc_client.get_ban_words(widget_token_info.author_id, ban_words_updated_at)
        if ban_words is not None:
            ban_words_updated_at = ban_words.updated_at
            message = WidgetMessage.make_ban_words_message(ban_words)
            await websocket.send_json(message.model_dump(mode="json", by_alias=True))

        ban_words_key = (key, "check_ban_words")
        await ws_alerts_manager.add_connection(ban_words_key, websocket)
        await alert_task_manager.start_single_schedule_task(
            ban_words_key,
            config.CHECK_NEW_BAN_WORDS_INTERVAL,
            ws_alerts_manager.broadcast_ban_words,
            ban_words_key,
            widget_token_info.author_id,
            TimestampPollState(updated_at=ban_words_updated_at),
        )

        async def _stop_ban_words_tasks():
            await alert_task_manager.stop_single_async_task(ban_words_key)

        ws_alerts_manager.register_on_empty(ban_words_key, _stop_ban_words_tasks)

    if get_moderation_settings:
        moderation_settings_updated_at = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
        moderation_settings = await moderation_settings_grpc_client.get_moderation_settings(
            widget_token_info.author_id, moderation_settings_updated_at
        )

        moderation_settings_key = (key, "check_moderation_settings")
        if moderation_settings is not None:
            moderation_settings_updated_at = moderation_settings.updated_at
            message = WidgetMessage.make_moderation_settings_message(moderation_settings)
            await ws_alerts_manager.add_connection(moderation_settings_key, websocket)
            await websocket.send_json(message.model_dump(mode="json", by_alias=True))

        async def _stop_moderation_settings_tasks():
            await alert_task_manager.stop_single_async_task(moderation_settings_key)

        ws_alerts_manager.register_on_empty(moderation_settings_key, _stop_moderation_settings_tasks)

        await alert_task_manager.start_single_schedule_task(
            moderation_settings_key,
            config.CHECK_NEW_MODERATION_SETTINGS_INTERVAL,
            ws_alerts_manager.broadcast_moderation_settings,
            moderation_settings_key,
            widget_token_info.author_id,
            TimestampPollState(updated_at=moderation_settings_updated_at),
        )

    if get_pending_donations:
        pending_donations = await alerts_grpc_client.get_pending_donations(widget_token_info.author_id)
        message = WidgetMessage.make_pending_alerts_message(pending_donations)
        await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    if get_connected_groups_info:
        connected_groups_info_key = (key, "connected_groups_info")
        await ws_alerts_manager.add_connection(connected_groups_info_key, websocket)
        connected_groups_poll = ConnectedGroupsPollState()
        await ws_alerts_manager.broadcast_connected_groups_info(
            connected_groups_info_key, widget_token_info.author_id, connected_groups_poll
        )
        await alert_task_manager.start_single_schedule_task(
            connected_groups_info_key,
            config.CHECK_MAX_GROUPS_DURATION_INTERVAL,
            ws_alerts_manager.broadcast_connected_groups_info,
            connected_groups_info_key,
            widget_token_info.author_id,
            connected_groups_poll,
        )

        async def _stop_check_max_groups_duration_tasks():
            await alert_task_manager.stop_single_async_task(connected_groups_info_key)

        ws_alerts_manager.register_on_empty(connected_groups_info_key, _stop_check_max_groups_duration_tasks)

    if statistic_widget_setting_id:
        statistic_widget_settings = await top_donaters_grpc_client.get_statistic_widget_settings(
            widget_token_info.author_id, statistic_widget_setting_id
        )
        if not statistic_widget_settings or statistic_widget_settings.user != widget_token_info.author_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "statistic widget settings not found")

        message = WidgetMessage.make_statistic_widget_settings_message(statistic_widget_settings)
        await websocket.send_json(message.model_dump(mode="json", by_alias=True))

        last_donations_list = await donations_grpc_client.get_last_donations_list(
            widget_token_info.author_id, statistic_widget_settings.elements_count
        )
        message = WidgetMessage.make_last_donations_list_message(last_donations_list)

        await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    exchange, queue = await rabbitmq.declare_queue(config.ALERTS_EXCHANGE, str(key))
    exchange, statuses_queue = await rabbitmq.declare_queue(config.ALERTS_EXCHANGE, config.ALERT_STATUS_QUEUE)

    await alert_task_manager.start_single_async_task(
        (key, "listen_rabbit"),
        rabbitmq.queue_iter,
        queue,
        ws_alerts_manager.on_rmq_message(key, widget_token_info.author_id),
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
    await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    exchange, queue = await rabbitmq.declare_queue(config.CAMPAIGNS_EXCHANGE, f"campaigns_{campaign_id}")

    key = (campaign_id, 1)

    async def _stop_campaign_tasks():
        await campaign_task_manager.stop_single_async_task(key)

    ws_campaigns_manager.register_on_empty(campaign_id, _stop_campaign_tasks)

    await campaign_task_manager.start_single_async_task(
        key,
        rabbitmq.queue_iter,
        queue,
        ws_campaigns_manager.on_rmq_message(campaign_id),
    )

    await ws_campaigns_manager.listen(campaign_id, websocket)


@widgets_router.websocket("/top_donaters/")
async def websocket_top_donaters_endpoint(
    websocket: WebSocket,
    setting_id: int,
    widget_token_info: WidgetTokenInfo = Depends(parse_widget_token),
):
    author_id = widget_token_info.author_id
    statistic_widget_settings = await top_donaters_grpc_client.get_statistic_widget_settings(author_id, setting_id)
    if not statistic_widget_settings or statistic_widget_settings.user != author_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "statistic widget settings not found")

    await ws_top_donaters_manager.connect(setting_id, websocket)
    ws_top_donaters_manager.register_setting(
        setting_id, author_id, statistic_widget_settings.period, statistic_widget_settings.elements_count
    )

    async def _stop_top_donaters_tasks():
        author_id_to_stop = ws_top_donaters_manager.unregister_setting(setting_id)
        if author_id_to_stop is not None:
            await top_donaters_task_manager.stop_single_async_task((author_id_to_stop, "listen_rabbit"))

    ws_top_donaters_manager.register_on_empty(setting_id, _stop_top_donaters_tasks)

    message = WidgetMessage.make_statistic_widget_settings_message(statistic_widget_settings)
    await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    time_now = datetime.datetime.now(datetime.timezone.utc)
    period_days = 1
    match statistic_widget_settings.period:
        case "all_time":
            period_days = 365
        case "last_month":
            period_days = 30
        case "last_week":
            period_days = 7
        case "last_day":
            period_days = 1

    start_time = time_now - datetime.timedelta(days=period_days)

    union_by_donor_names_list = await donations_grpc_client.get_union_by_donor_names_list(
        author_id,
        start_time,
        time_now,
        statistic_widget_settings.elements_count,
    )
    message = WidgetMessage.make_union_by_donor_names_list_message(union_by_donor_names_list)
    await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    await ws_top_donaters_manager.seed_cache_if_empty(
        author_id, statistic_widget_settings.period, union_by_donor_names_list
    )

    _exchange, queue = await rabbitmq.declare_queue(
        config.ALERTS_EXCHANGE,
        f"top_donaters_{author_id}",
    )

    await top_donaters_task_manager.start_single_async_task(
        (author_id, "listen_rabbit"),
        rabbitmq.queue_iter,
        queue,
        ws_top_donaters_manager.on_rmq_message(author_id),
    )

    await ws_top_donaters_manager.listen(setting_id, websocket)


@widgets_router.websocket("/videos/")
async def websocket_videos_endpoint(
    websocket: WebSocket,
    widget_token_info: WidgetTokenInfo = Depends(parse_widget_token),
):
    author_id = widget_token_info.author_id
    widget_video_settings = await widget_video_settings_grpc_client.get_video_settings(
        author_id, datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    )
    if not widget_video_settings:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "widget video settings not found")

    await ws_videos_manager.connect(author_id, websocket)
    message = WidgetMessage.make_widget_video_settings_message(widget_video_settings)
    await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    widget_video_settings_key = (author_id, "broadcast_widget_video_settings")

    async def _stop_widget_video_settings_tasks():
        await ws_videos_manager.stop_single_async_task(widget_video_settings_key)

    ws_videos_manager.register_on_empty(author_id, _stop_widget_video_settings_tasks)

    await video_task_manager.start_single_schedule_task(
        widget_video_settings_key,
        config.CHECK_NEW_WIDGET_VIDEO_SETTINGS_INTERVAL,
        ws_videos_manager.broadcast_widget_video_settings,
        widget_video_settings_key,
        author_id,
        TimestampPollState(updated_at=widget_video_settings.updated_at),
    )

    widget_videos = await widget_videos_grpc_client.get_videos(
        author_id, datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    )
    if not widget_videos:
        widget_videos = []

    message = WidgetMessage.make_widget_videos_message(widget_videos)
    await websocket.send_json(message.model_dump(mode="json", by_alias=True))

    widget_videos_key = (author_id, "broadcast_widget_videos")

    async def _stop_widget_videos_tasks():
        await ws_videos_manager.stop_single_async_task(widget_videos_key)

    ws_videos_manager.register_on_empty(author_id, _stop_widget_videos_tasks)

    await video_task_manager.start_single_schedule_task(
        widget_videos_key,
        config.CHECK_NEW_WIDGET_VIDEOS_INTERVAL,
        ws_videos_manager.broadcast_widget_videos,
        widget_videos_key,
        author_id,
        TimestampPollState(updated_at=datetime.datetime.fromtimestamp(0, datetime.timezone.utc)),
    )

    exchange, queue = await rabbitmq.declare_queue(config.VIDEOS_EXCHANGE, f"videos_{author_id}")
    exchange, statuses_queue = await rabbitmq.declare_queue(config.VIDEOS_EXCHANGE, config.VIDEO_STATUS_QUEUE)

    await video_task_manager.start_single_async_task(
        (author_id, "listen_rabbit"),
        rabbitmq.queue_iter,
        queue,
        ws_videos_manager.on_rmq_message(author_id),
    )

    await ws_videos_manager.listen(author_id, websocket, get_videos_ws_messages_handler(author_id, exchange))
