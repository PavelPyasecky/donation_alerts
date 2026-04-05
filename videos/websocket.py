import datetime
import json

from aio_pika.abc import AbstractIncomingMessage
from models.widget_message import WidgetMessage
from utils.poll_states import TimestampPollState
from utils.websocket_manager import WSManager
from videos.grpc import widget_video_settings_grpc_client, widget_videos_grpc_client


class VideosWSManager(WSManager):
    async def broadcast_widget_video_settings(self, ws_key: any, author_id: int, poll: TimestampPollState):
        if not self.is_author_connected(ws_key):
            return False

        widget_video_settings = await widget_video_settings_grpc_client.get_video_settings(author_id, poll.updated_at)
        if widget_video_settings is None:
            return True

        poll.updated_at = widget_video_settings.updated_at

        message = WidgetMessage.make_widget_video_settings_message(widget_video_settings)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_widget_videos(self, ws_key: any, author_id: int, poll: TimestampPollState):
        if not self.is_author_connected(ws_key):
            return False

        widget_videos = await widget_videos_grpc_client.get_videos(author_id, poll.updated_at)
        if not widget_videos:
            return True

        if widget_videos:
            poll.updated_at = max(video.created_at for video in widget_videos)

        message = WidgetMessage.make_widget_videos_message(widget_videos)
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


ws_videos_manager = VideosWSManager()
