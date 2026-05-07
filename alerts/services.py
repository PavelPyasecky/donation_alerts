import datetime
import logging

from aio_pika import Message
from aio_pika.abc import AbstractExchange

from alerts.alers_state import alert_state_service
from alerts.alert_sequence import alert_sequence_service
from alerts.grpc import moderation_settings_grpc_client
from configs.constants import ZERO_DATETIME
from models.alert import ManualModerationAlertDecision, RabbitMQAlertStatus
from models.alert_state import WidgetAlertState
from models.widget_message import WidgetMessage, WidgetMessageTypes
from configs.redis import get_user_state_redis_conn
from configs import config
from utils.task_manager import TaskManager

logger = logging.getLogger(__name__)


async def is_manual_moderation_enabled(author_id: int) -> bool:
    moderation_settings = await moderation_settings_grpc_client.get_moderation_settings(author_id, ZERO_DATETIME)
    return bool(moderation_settings and moderation_settings.is_manual)


async def set_first_queued_alert_to_moderation(author_id: int) -> WidgetAlertState | None:
    if not await is_manual_moderation_enabled(author_id):
        return None

    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.current_alert_id is not None and current_state.status in ("moderation", "viewing"):
        return None

    sequence = await alert_sequence_service.get_sequence(author_id)
    if not sequence:
        return None

    first_item = sequence[0]
    return await alert_state_service.set_alert_state(
        author_id,
        current_alert_id=first_item.alert_id,
        start_moderating_at=datetime.datetime.now(datetime.timezone.utc),
        start_viewing_at=None,
        current_donation_id=first_item.donation_id,
        status="moderation",
    )


async def reset_manual_moderation_state(author_id: int) -> WidgetAlertState | None:
    await alert_sequence_service.clear_sequence(author_id)

    current_state = await alert_state_service.get_alert_state(author_id)
    if current_state.status != "moderation":
        return None

    return await alert_state_service.set_alert_state(
        author_id,
        current_alert_id=None,
        start_moderating_at=None,
        start_viewing_at=None,
        current_donation_id=None,
        status="idle",
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
                        is_locked_on_manual_moderation = (
                            is_manual_moderation
                            and current_state.status == "moderation"
                            and current_state.current_alert_id is not None
                        )
                        if is_locked_on_manual_moderation:
                            next_state = current_state
                        elif not is_manual_moderation and alert_state.status == "moderation":
                            reset_state = await reset_manual_moderation_state(author_id)
                            next_state = reset_state if reset_state is not None else current_state
                        elif is_manual_moderation and alert_state.status == "moderation":
                            queued_state = await set_first_queued_alert_to_moderation(author_id)
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
                            queued_state = await set_first_queued_alert_to_moderation(author_id)
                            if queued_state is not None:
                                next_state = queued_state
                        await ws_manager.broadcast(
                            author_id,
                            WidgetMessage.make_alert_state_message(next_state).model_dump(mode="json", by_alias=True),
                        )
                    case "allow" | "decline":
                        payload = ManualModerationAlertDecision.model_validate(message.data.model_dump())
                        current_state = await alert_state_service.get_alert_state(author_id)
                        next_sequence_item = await alert_sequence_service.advance_past(
                            author_id,
                            payload.alert_id,
                            payload.donation_id,
                        )
                        if message.action == "allow":
                            next_state = await alert_state_service.set_alert_state(
                                author_id,
                                current_alert_id=payload.alert_id,
                                start_moderating_at=current_state.start_moderating_at,
                                start_viewing_at=datetime.datetime.now(datetime.timezone.utc),
                                current_donation_id=payload.donation_id,
                                status="viewing",
                            )
                        elif next_sequence_item is not None:
                            next_state = await alert_state_service.set_alert_state(
                                author_id,
                                current_alert_id=next_sequence_item.alert_id,
                                start_moderating_at=datetime.datetime.now(datetime.timezone.utc),
                                start_viewing_at=None,
                                current_donation_id=next_sequence_item.donation_id,
                                status="moderation",
                            )
                        else:
                            next_state = await alert_state_service.set_alert_state(
                                author_id,
                                current_alert_id=None,
                                start_moderating_at=None,
                                start_viewing_at=None,
                                current_donation_id=None,
                                status="idle",
                            )
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
