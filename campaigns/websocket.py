import json

from aio_pika.abc import AbstractIncomingMessage

from models.widget_message import WidgetMessage
from utils.websocket_manager import WSManager


class CampaignsWSManager(WSManager):
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


ws_campaigns_manager = CampaignsWSManager()
