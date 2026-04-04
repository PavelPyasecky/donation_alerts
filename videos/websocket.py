import datetime
import json

from aio_pika.abc import AbstractIncomingMessage
from models.widget_message import WidgetMessage
from utils.poll_states import TimestampPollState, VideoCatalogPollState
from utils.websocket_manager import WSManager
from videos.services import get_video_state, sync_video_queue_with_catalog
from videos.grpc import widget_video_settings_grpc_client, widget_videos_grpc_client

ZERO_DATETIME = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)


def _videos_fingerprint(widget_videos: list) -> str:
    return json.dumps(
        [
            {
                "id": video.id,
                "url": video.url,
                "created_at": video.created_at.isoformat(),
            }
            for video in widget_videos
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )


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

        widget_videos = await widget_videos_grpc_client.get_videos(author_id, ZERO_DATETIME)
        video_state = await get_video_state(author_id)
        video_queue, queue_changed = await sync_video_queue_with_catalog(
            author_id,
            widget_videos or [],
            widget_video_settings.play_randomly,
            video_state.video_id,
        )
        if queue_changed:
            queue_message = WidgetMessage.make_video_queue_message(video_queue)
            await self.broadcast(ws_key, queue_message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_widget_videos(self, ws_key: any, author_id: int, poll: VideoCatalogPollState):
        if not self.is_author_connected(ws_key):
            return False

        widget_videos = await widget_videos_grpc_client.get_videos(author_id, ZERO_DATETIME)
        widget_videos = widget_videos or []
        fingerprint = _videos_fingerprint(widget_videos)
        if fingerprint == poll.fingerprint:
            return True

        poll.fingerprint = fingerprint

        widget_video_settings = await widget_video_settings_grpc_client.get_video_settings(author_id, ZERO_DATETIME)
        if widget_video_settings is None:
            return True

        video_state = await get_video_state(author_id)
        video_queue, _ = await sync_video_queue_with_catalog(
            author_id,
            widget_videos,
            widget_video_settings.play_randomly,
            video_state.video_id,
        )
        queue_message = WidgetMessage.make_video_queue_message(video_queue)
        await self.broadcast(ws_key, queue_message.model_dump(mode="json", by_alias=True))
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
