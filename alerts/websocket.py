import datetime
import json

from aio_pika.abc import AbstractIncomingMessage

from alerts.grpc import alert_settings_group_grpc_client
from models.widget_message import WidgetMessage
from utils.websocket_manager import WSManager


class AlertsWSManager(WSManager):
    async def broadcast_alerts_group(
        self, ws_key: any, author_id: int, group_id: int, updated_at: list[datetime.datetime]
    ):
        if not self.is_author_connected(ws_key):
            return False

        alert_settings_group = await alert_settings_group_grpc_client.get_alert_settings_group_filter_updated_at(
            author_id, group_id, updated_at[0]
        )
        if alert_settings_group is None:
            return True

        updated_at[0] = alert_settings_group.updated_at

        message = WidgetMessage.make_alert_settings_group_message(alert_settings_group)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    def on_rmq_message(self, ws_key: any):
        async def _on_rmq_message(message: AbstractIncomingMessage):
            if not self.is_author_connected(ws_key):
                await message.nack(requeue=True)
                return False
            data = json.loads(message.body.decode())
            message_model = WidgetMessage(**data)
            await self.broadcast(ws_key, message_model.model_dump(mode="json", by_alias=True))
            return True

        return _on_rmq_message


class CampaignsWSManager(WSManager):
    pass


ws_alerts_manager = AlertsWSManager()
ws_campaigns_manager = CampaignsWSManager()
