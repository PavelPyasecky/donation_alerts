import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Literal

from aio_pika import Message
from aio_pika.abc import AbstractExchange

from alerts.alers_state import alert_state_service
from alerts.alert_sequence import AlertSequenceData, alert_sequence_service
from alerts.grpc import moderation_settings_grpc_client
from configs.constants import NOW, ZERO_DATETIME
from models.alert import Alert, ManualModerationAlertDecision, RabbitMQAlertStatus
from models.alert_state import WidgetAlertState
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager


if TYPE_CHECKING:
    from alerts.websocket import AlertsWSManager

logger = logging.getLogger(__name__)


def get_ws_messages_handler(
    author_id: int,
    exchange: AbstractExchange,
    alert_task_manager: "AlertTaskManager",
    ws_manager: "AlertsWSManager",
    ws_key: any,
):
    async def wrapper(message_data: dict):
        message = WidgetMessage(**message_data)
        match message.type_:
            case WidgetMessageTypes.update:
                match message.action:
                    case "alert_status":
                        alert_status = RabbitMQAlertStatus(author_id=author_id, **message.data.model_dump())
                        await exchange.publish(
                            message=Message(body=alert_status.model_dump_json().encode()),
                            routing_key=config.ALERT_STATUS_QUEUE,
                        )
                    case "allow" | "skip":
                        await alert_task_manager.stop_single_async_task((author_id, "state_machine"))
                        await alert_task_manager.start_single_async_task(
                            (author_id, "state_machine"),
                            run_alert_state_processing,
                            author_id,
                            ws_manager,
                            ws_key,
                            message.action,
                        )

    return wrapper


async def mark_streamer_online(author_id: int):
    user_state_redis_conn = get_user_state_redis_conn()
    await user_state_redis_conn.set(
        config.STREAMER_ONLINE_KEY.format(author_id=author_id),
        1,
        ex=config.STREAMER_PRESENCE_TTL_SECONDS,
    )


async def refresh_streamer_presence_ttl(author_id: int) -> None:
    conn = get_user_state_redis_conn()
    ttl = config.STREAMER_PRESENCE_TTL_SECONDS
    online_key = config.STREAMER_ONLINE_KEY.format(author_id=author_id)
    groups_key = config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id)
    await conn.expire(online_key, ttl)
    await conn.expire(groups_key, ttl)


async def mark_streamer_offline(author_id: int):
    user_state_redis_conn = get_user_state_redis_conn()
    await user_state_redis_conn.delete(config.STREAMER_ONLINE_KEY.format(author_id=author_id))
    await user_state_redis_conn.delete(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id))


async def mark_streamer_group_connected(author_id: int, group_id: int) -> None:
    redis_conn = get_user_state_redis_conn()
    groups_key = config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id)
    await redis_conn.sadd(groups_key, group_id)
    await redis_conn.expire(groups_key, config.STREAMER_PRESENCE_TTL_SECONDS)


async def mark_streamer_group_disconnected(author_id: int, group_id: int) -> None:
    redis_conn = get_user_state_redis_conn()
    groups_key = config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id)
    await redis_conn.srem(groups_key, group_id)
    groups_count = await redis_conn.scard(groups_key)
    if groups_count == 0:
        await redis_conn.delete(config.STREAMER_ONLINE_KEY.format(author_id=author_id))
        await redis_conn.delete(groups_key)


async def get_connected_groups(author_id: int) -> list[int]:
    redis_conn = get_user_state_redis_conn()
    groups = await redis_conn.smembers(config.STREAMER_CONNECTED_GROUPS_KEY.format(author_id=author_id))
    return sorted(int(group_id) for group_id in groups)


class AlertTaskManager(TaskManager):
    pass


alert_task_manager = AlertTaskManager()


IS_MANUAL_MODERATION_DURATION_CODE = -1


async def _process_alert_state(
    author_id: int,
    alert_sequence_data: AlertSequenceData,
    alert_state: WidgetAlertState,
    first_alert: Alert,
    action: Literal["allow", "skip"] | None = None,
):
    def _need_moderation(alert_sequence_data: AlertSequenceData, amount: str) -> bool:
        return (
            alert_sequence_data.moderation_settings.is_active
            and alert_sequence_data.moderation_settings.activation_amount is not None
            and alert_sequence_data.moderation_settings.activation_amount <= amount
        )

    def _is_manual_moderation_enabled(alert_sequence_data: AlertSequenceData, amount: str) -> bool:
        return _need_moderation(alert_sequence_data, amount) and alert_sequence_data.moderation_settings.is_manual

    next_trigger_delay = 1
    need_broadcast = False

    match alert_state.status:
        case "moderation":
            if action is None or action == "allow":
                next_trigger_delay = alert_sequence_data.get_max_viewing_duration_seconds_by_amount(first_alert.amount)
                alert_state = await alert_state_service.set_alert_state(
                    author_id,
                    current_alert_id=alert_state.current_alert_id,
                    current_donation_id=alert_state.current_donation_id,
                    start_moderating_at=alert_state.start_moderating_at,
                    start_viewing_at=NOW(),
                    status="viewing",
                    duration_seconds=next_trigger_delay,
                )
                need_broadcast = True
            elif action == "skip":
                if first_alert:
                    alert_sequence_service.pop_first_sequence_item(author_id)
                    need_moderation = (
                        alert_sequence_data.moderation_settings.need_moderation(first_alert.amount)
                        if alert_sequence_data.moderation_settings is not None
                        else False
                    )
                    next_trigger_delay = (
                        alert_sequence_data.get_moderation_duration_seconds()
                        if need_moderation
                        else alert_sequence_data.get_max_viewing_duration_seconds_by_amount(first_alert.amount)
                    )
                    need_manual_moderation = _is_manual_moderation_enabled(alert_sequence_data, first_alert.amount)
                    if need_manual_moderation:
                        next_trigger_delay = IS_MANUAL_MODERATION_DURATION_CODE
                    alert_state = await alert_state_service.set_alert_state(
                        author_id,
                        current_alert_id=first_alert.alert_id,
                        current_donation_id=first_alert.donation_id,
                        start_moderating_at=NOW() if need_moderation else None,
                        start_viewing_at=None if need_moderation else NOW(),
                        status="moderation" if need_moderation else "viewing",
                        duration_seconds=next_trigger_delay,
                    )
                    need_broadcast = True
        case "viewing" | "idle":
            if first_alert:
                alert_sequence_service.pop_first_sequence_item(author_id)
                need_moderation = (
                    alert_sequence_data.moderation_settings.need_moderation(first_alert.amount)
                    if alert_sequence_data.moderation_settings is not None
                    else False
                )
                need_manual_moderation = _is_manual_moderation_enabled(alert_sequence_data, first_alert.amount)
                next_trigger_delay = (
                    alert_sequence_data.get_moderation_duration_seconds()
                    if need_moderation
                    else alert_sequence_data.get_max_viewing_duration_seconds_by_amount(first_alert.amount)
                )
                if need_manual_moderation:
                    next_trigger_delay = IS_MANUAL_MODERATION_DURATION_CODE
                alert_state = await alert_state_service.set_alert_state(
                    author_id,
                    current_alert_id=first_alert.alert_id,
                    current_donation_id=first_alert.donation_id,
                    start_moderating_at=NOW() if need_moderation else None,
                    start_viewing_at=None if need_moderation else NOW(),
                    status="moderation" if need_moderation else "viewing",
                    duration_seconds=next_trigger_delay,
                )
                need_broadcast = True

    return next_trigger_delay, alert_state, need_broadcast


async def run_alert_state_processing(
    author_id: int, ws_manager: "AlertsWSManager", ws_key: any, action: Literal["allow", "skip"] | None = None
):
    while True:
        if not ws_manager.is_author_connected(ws_key):
            break
        alert_sequence_data = alert_sequence_service.get_alert_sequence_data(author_id)
        if not alert_sequence_data.connected_groups:
            await asyncio.sleep(5)
            continue

        alert_state = await alert_state_service.get_alert_state(author_id)

        if alert_state.duration_seconds == IS_MANUAL_MODERATION_DURATION_CODE and action is None:
            break

        need_broadcast = False

        first_alert = alert_sequence_service.get_first_sequence_item(author_id)

        action_duration_until = None
        match alert_state.status:
            case "moderation":
                action_duration_until = alert_state.start_moderating_at + datetime.timedelta(
                    seconds=alert_state.duration_seconds
                )
            case "viewing":
                action_duration_until = alert_state.start_viewing_at + datetime.timedelta(
                    seconds=alert_sequence_data.get_max_viewing_duration_seconds_by_amount(first_alert.amount)
                )
            case "idle":
                action_duration_until = None

        if action_duration_until is not None and action_duration_until > NOW() and action is None:
            next_trigger_delay = max((action_duration_until - NOW()).total_seconds(), 1)
            await asyncio.sleep(next_trigger_delay)
            continue

        next_trigger_delay, alert_state, need_broadcast = await _process_alert_state(
            author_id, alert_sequence_data, alert_state, first_alert, action
        )
        action = None

        if need_broadcast:
            await ws_manager.broadcast(
                ws_key,
                WidgetMessage.make_alert_state_message(alert_state).model_dump(
                    mode="json",
                    by_alias=True,
                ),
            )
        if next_trigger_delay == IS_MANUAL_MODERATION_DURATION_CODE:
            break
        await asyncio.sleep(next_trigger_delay)
