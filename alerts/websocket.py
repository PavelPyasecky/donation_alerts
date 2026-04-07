import datetime
import json

from aio_pika.abc import AbstractIncomingMessage

from alerts.grpc import (
    alert_settings_group_grpc_client,
    alert_settings_grpc_client,
    ban_words_grpc_client,
    moderation_settings_grpc_client,
)
from alerts.poll_state import ConnectedGroupsPollState
from alerts.services import (
    get_connected_groups,
    mark_streamer_group_connected,
    mark_streamer_group_disconnected,
    mark_streamer_offline,
    mark_streamer_online,
    refresh_streamer_presence_ttl,
)
from models.widget_message import ConnectedGroupsInfo, WidgetMessage, WidgetMessageTypes
from utils.poll_states import TimestampPollState
from utils.websocket_manager import WSManager


class AlertsWSManager(WSManager):
    async def mark_group_widget_connected(self, author_id: int, group_id: int) -> None:
        await mark_streamer_online(author_id)
        await mark_streamer_group_connected(author_id, group_id)

    async def mark_group_widget_disconnected(self, author_id: int, group_id: int) -> None:
        await mark_streamer_group_disconnected(author_id, group_id)
        connected_groups = await get_connected_groups(author_id)
        if not connected_groups:
            await mark_streamer_offline(author_id)

    async def broadcast_alerts_group(
        self, ws_key: any, author_id: int, group_id: int, poll: TimestampPollState
    ):
        if not self.is_author_connected(ws_key):
            return False

        await refresh_streamer_presence_ttl(author_id)

        alert_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
            author_id, group_id, poll.updated_at
        )
        if alert_settings_group is None:
            return True

        poll.updated_at = alert_settings_group.updated_at

        message = WidgetMessage.make_alert_settings_group_message(alert_settings_group)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_connected_groups_info(self, ws_key: any, author_id: int, poll: ConnectedGroupsPollState):
        if not self.is_author_connected(ws_key):
            return False

        await refresh_streamer_presence_ttl(author_id)

        old_connected_groups_ids = poll.connected_group_ids
        poll.connected_group_ids = await get_connected_groups(author_id)
        groups = await alert_settings_group_grpc_client.get_alert_settings_groups(
            author_id,
            poll.connected_group_ids,
            poll.updated_at
            if old_connected_groups_ids == poll.connected_group_ids
            else datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
        )

        poll.updated_at = datetime.datetime.now(datetime.timezone.utc)

        connected_groups_info = ConnectedGroupsInfo(groups=groups, connected_groups_ids=poll.connected_group_ids)
        message = WidgetMessage.make_connected_groups_info_message(connected_groups_info)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_ban_words(self, ws_key: any, author_id: int, poll: TimestampPollState):
        ban_words = await ban_words_grpc_client.get_ban_words(author_id, poll.updated_at)
        if ban_words is None:
            return True
        poll.updated_at = datetime.datetime.now(datetime.timezone.utc)
        message = WidgetMessage.make_ban_words_message(ban_words)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_moderation_settings(self, ws_key: any, author_id: int, poll: TimestampPollState):
        moderation_settings = await moderation_settings_grpc_client.get_moderation_settings(author_id, poll.updated_at)
        if moderation_settings is None:
            return True
        poll.updated_at = moderation_settings.updated_at
        message = WidgetMessage.make_moderation_settings_message(moderation_settings)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    def on_rmq_message(self, ws_key: any, author_id: int):
        async def _on_rmq_message(message: AbstractIncomingMessage):
            if not self.is_author_connected(ws_key):
                await message.nack(requeue=True)
                return False
            data = json.loads(message.body.decode())
            message_model = WidgetMessage(**data)

            match message_model.type_:
                case WidgetMessageTypes.update:
                    match message_model.action:
                        case "test_alert":
                            alert_setting = await alert_settings_grpc_client.get_alert_settings(
                                author_id, message_model.data.setting
                            )
                            message_model.data.setting = alert_setting

            await self.broadcast(ws_key, message_model.model_dump(mode="json", by_alias=True))
            return True

        return _on_rmq_message


ws_alerts_manager = AlertsWSManager()
