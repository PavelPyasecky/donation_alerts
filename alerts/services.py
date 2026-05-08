import datetime
import logging
from decimal import Decimal, InvalidOperation

from aio_pika import Message
from aio_pika.abc import AbstractExchange

from alerts.alers_state import alert_state_service
from alerts.alert_sequence import AlertSequenceItem, alert_sequence_service
from alerts.grpc import alert_settings_grpc_client, moderation_settings_grpc_client
from configs.constants import ZERO_DATETIME
from models.alert import Alert, AlertSetting, ManualModerationAlertDecision, RabbitMQAlertStatus
from models.alert_state import WidgetAlertState
from models.settings import ModerationSettings
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager

logger = logging.getLogger(__name__)


def _playback_task_key(author_id: int) -> tuple[int, str]:
    return author_id, "alert_playback"


def _is_same_alert(state: WidgetAlertState, item: AlertSequenceItem) -> bool:
    return state.current_alert_id == item.alert_id and (
        item.donation_id is None or state.current_donation_id == item.donation_id
    )


def _parse_amount(amount: str | int | float | Decimal | None) -> Decimal | None:
    if amount in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return None


def _should_moderate(settings: ModerationSettings | None, alert: Alert | None) -> bool:
    if settings is None or alert is None or not settings.is_active:
        return False

    activation_amount = _parse_amount(settings.activation_amount)
    alert_amount = _parse_amount(alert.amount)
    if activation_amount is None or alert_amount is None:
        return False

    return alert_amount < activation_amount


def _get_viewing_duration(alert: Alert | None) -> float:
    if alert is None or not isinstance(alert.setting, AlertSetting):
        return 0
    return max(alert.setting.sound_duration or 0, alert.setting.message_duration or 0)


async def _resolve_item_alert(author_id: int, item: AlertSequenceItem) -> Alert | None:
    alert = item.alert
    if alert is None:
        return None
    if isinstance(alert.setting, int):
        setting = await alert_settings_grpc_client.get_alert_settings(author_id, alert.setting)
        if setting is not None:
            alert = alert.model_copy(update={"setting": setting})
            item.alert = alert
    return alert


async def get_moderation_settings(author_id: int) -> ModerationSettings | None:
    return await moderation_settings_grpc_client.get_moderation_settings(author_id, ZERO_DATETIME)


async def is_manual_moderation_enabled(author_id: int) -> bool:
    moderation_settings = await get_moderation_settings(author_id)
    return bool(moderation_settings and moderation_settings.is_manual)


async def set_first_queued_alert_to_moderation(author_id: int, ws_manager=None) -> WidgetAlertState | None:
    return await start_alert_playback(author_id, ws_manager)


async def reset_manual_moderation_state(author_id: int) -> WidgetAlertState | None:
    return None


async def stop_alert_playback(author_id: int) -> None:
    await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))


async def start_alert_playback(author_id: int, ws_manager=None) -> WidgetAlertState | None:
    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.current_alert_id is not None and current_state.status in ("moderation", "viewing"):
        await schedule_current_alert_timeout(author_id, ws_manager)
        return None

    sequence = await alert_sequence_service.get_sequence(author_id)
    if not sequence:
        if current_state.status == "idle":
            return None
        await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))
        return await alert_state_service.set_alert_state(
            author_id,
            current_alert_id=None,
            start_moderating_at=None,
            start_viewing_at=None,
            current_donation_id=None,
            status="idle",
        )

    return await start_sequence_item(author_id, sequence[0], ws_manager)


async def start_sequence_item(
    author_id: int,
    item: AlertSequenceItem,
    ws_manager=None,
) -> WidgetAlertState:
    moderation_settings = await get_moderation_settings(author_id)
    alert = await _resolve_item_alert(author_id, item)
    await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))

    if _should_moderate(moderation_settings, alert):
        next_state = await alert_state_service.set_alert_state(
            author_id,
            current_alert_id=item.alert_id,
            start_moderating_at=datetime.datetime.now(datetime.timezone.utc),
            start_viewing_at=None,
            current_donation_id=item.donation_id,
            status="moderation",
        )
        if moderation_settings is not None and not moderation_settings.is_manual:
            await schedule_moderation_timeout(author_id, item, moderation_settings.duration, ws_manager)
        return next_state

    next_state = await set_sequence_item_to_viewing(author_id, item, ws_manager)
    return next_state


async def set_sequence_item_to_viewing(
    author_id: int,
    item: AlertSequenceItem,
    ws_manager=None,
) -> WidgetAlertState:
    alert = await _resolve_item_alert(author_id, item)
    next_state = await alert_state_service.set_alert_state(
        author_id,
        current_alert_id=item.alert_id,
        start_moderating_at=None,
        start_viewing_at=datetime.datetime.now(datetime.timezone.utc),
        current_donation_id=item.donation_id,
        status="viewing",
    )
    await schedule_viewing_timeout(author_id, item, _get_viewing_duration(alert), ws_manager)
    return next_state


async def schedule_moderation_timeout(
    author_id: int,
    item: AlertSequenceItem,
    delay_seconds: float,
    ws_manager=None,
) -> None:
    await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))
    await alert_task_manager.start_single_delayed_task(
        _playback_task_key(author_id),
        max(delay_seconds, 0),
        finish_timed_moderation,
        author_id,
        item,
        ws_manager,
    )


async def schedule_viewing_timeout(
    author_id: int,
    item: AlertSequenceItem,
    delay_seconds: float,
    ws_manager=None,
) -> None:
    await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))
    await alert_task_manager.start_single_delayed_task(
        _playback_task_key(author_id),
        max(delay_seconds, 0),
        finish_viewing,
        author_id,
        item,
        ws_manager,
    )


async def schedule_current_alert_timeout(author_id: int, ws_manager=None) -> None:
    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.current_alert_id is None:
        return

    item = await alert_sequence_service.get_item(
        author_id,
        current_state.current_alert_id,
        current_state.current_donation_id,
    )
    if item is None:
        return

    if current_state.status == "moderation":
        moderation_settings = await get_moderation_settings(author_id)
        alert = await _resolve_item_alert(author_id, item)
        if (
            moderation_settings is None
            or moderation_settings.is_manual
            or not _should_moderate(moderation_settings, alert)
        ):
            return
        elapsed = 0
        if current_state.start_moderating_at is not None:
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - current_state.start_moderating_at).total_seconds()
        await schedule_moderation_timeout(author_id, item, moderation_settings.duration - elapsed, ws_manager)
    elif current_state.status == "viewing":
        alert = await _resolve_item_alert(author_id, item)
        elapsed = 0
        if current_state.start_viewing_at is not None:
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - current_state.start_viewing_at).total_seconds()
        await schedule_viewing_timeout(author_id, item, _get_viewing_duration(alert) - elapsed, ws_manager)


async def finish_timed_moderation(author_id: int, item: AlertSequenceItem, ws_manager=None) -> None:
    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.status != "moderation" or not _is_same_alert(current_state, item):
        return

    next_state = await set_sequence_item_to_viewing(author_id, item, ws_manager)
    await broadcast_alert_state(author_id, next_state, ws_manager)


async def finish_viewing(author_id: int, item: AlertSequenceItem, ws_manager=None) -> None:
    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.status != "viewing" or not _is_same_alert(current_state, item):
        return

    await alert_sequence_service.advance_past(author_id, item.alert_id, item.donation_id)
    next_state = await start_alert_playback(author_id, ws_manager)
    if next_state is None:
        next_state = await alert_state_service.get_alert_state(author_id)
    await broadcast_alert_state(author_id, next_state, ws_manager)


async def broadcast_alert_state(author_id: int, alert_state: WidgetAlertState, ws_manager=None) -> None:
    if ws_manager is None:
        return
    await ws_manager.broadcast(
        author_id,
        WidgetMessage.make_alert_state_message(alert_state).model_dump(mode="json", by_alias=True),
    )


def get_ws_messages_handler(author_id: int, exchange: AbstractExchange, ws_manager):
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
                    case "alert_state":
                        alert_state = WidgetAlertState.model_validate(message.data.model_dump())
                        current_state = await alert_state_service.get_alert_state(author_id)
                        is_manual_moderation = await is_manual_moderation_enabled(author_id)
                        is_locked_on_current_moderation = (
                            current_state.status == "moderation"
                            and current_state.current_alert_id is not None
                            and alert_state.status == "moderation"
                            and alert_state.current_alert_id != current_state.current_alert_id
                        )
                        if is_locked_on_current_moderation:
                            await schedule_current_alert_timeout(author_id, ws_manager)
                            next_state = current_state
                        elif is_manual_moderation and alert_state.status == "moderation":
                            queued_state = await set_first_queued_alert_to_moderation(author_id, ws_manager)
                            next_state = queued_state if queued_state is not None else current_state
                        else:
                            start_moderating_at = alert_state.start_moderating_at
                            if alert_state.status == "moderation" and start_moderating_at is None:
                                start_moderating_at = datetime.datetime.now(datetime.timezone.utc)
                            next_state = await alert_state_service.set_alert_state(
                                author_id,
                                current_alert_id=alert_state.current_alert_id,
                                start_moderating_at=start_moderating_at,
                                start_viewing_at=alert_state.start_viewing_at,
                                current_donation_id=alert_state.current_donation_id,
                                status=alert_state.status,
                            )
                            queued_state = await set_first_queued_alert_to_moderation(author_id, ws_manager)
                            if queued_state is not None:
                                next_state = queued_state
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage.make_alert_state_message(next_state).model_dump(mode="json", by_alias=True),
                        )
                    case "allow" | "decline":
                        payload = ManualModerationAlertDecision.model_validate(message.data.model_dump())
                        await alert_task_manager.stop_single_async_task(_playback_task_key(author_id))
                        current_item = await alert_sequence_service.get_item(
                            author_id,
                            payload.alert_id,
                            payload.donation_id,
                        )
                        if current_item is None:
                            current_item = AlertSequenceItem(
                                alert_id=payload.alert_id,
                                donation_id=payload.donation_id,
                            )
                        if message.action == "allow":
                            next_state = await set_sequence_item_to_viewing(author_id, current_item, ws_manager)
                        else:
                            await alert_sequence_service.advance_past(
                                author_id,
                                payload.alert_id,
                                payload.donation_id,
                            )
                            next_state = await start_alert_playback(author_id, ws_manager)
                            if next_state is None:
                                next_state = await alert_state_service.get_alert_state(author_id)
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage.make_alert_state_message(next_state).model_dump(
                                mode="json",
                                by_alias=True,
                            ),
                        )
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage(
                                type=WidgetMessageTypes.update,
                                action=message.action,
                                data=payload,
                            ).model_dump(mode="json", by_alias=True),
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
