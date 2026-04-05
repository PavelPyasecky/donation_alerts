import datetime
import json

from aio_pika.abc import AbstractIncomingMessage
from models.widget_message import WidgetMessage
from utils.poll_states import TimestampPollState
from utils.websocket_manager import WSManager
from videos.video_state import video_state_service
from videos.grpc import widget_video_settings_grpc_client, widget_videos_grpc_client

ZERO_DATETIME = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)


class VideosWSManager(WSManager):
    async def build_video_state_and_queue_messages(
        self,
        author_id: int,
        widget_videos: list | None,
        play_randomly: bool,
    ):
        widget_videos = widget_videos or []
        video_state = await video_state_service.get_video_state(author_id)
        if play_randomly == (await video_state_service.get_stored_video_queue(author_id)).play_randomly:
            video_state, video_queue = await video_state_service.sync_queue_with_original_videos(author_id, widget_videos)
        else:
            video_state, video_queue = await video_state_service.sync_queue_with_play_randomly(
                author_id,
                widget_videos,
                play_randomly,
            )

        latest_updated_at = max((video.created_at for video in widget_videos), default=ZERO_DATETIME)
        return (
            WidgetMessage.make_video_state_message(video_state),
            WidgetMessage.make_video_queue_message(video_queue),
            latest_updated_at,
        )

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
        _, queue_message, _ = await self.build_video_state_and_queue_messages(
            author_id,
            widget_videos=widget_videos,
            play_randomly=widget_video_settings.play_randomly,
        )
        await self.broadcast(ws_key, queue_message.model_dump(mode="json", by_alias=True))
        return True

    async def broadcast_widget_videos(self, ws_key: any, author_id: int, poll: TimestampPollState):
        if not self.is_author_connected(ws_key):
            return False

        widget_videos = await widget_videos_grpc_client.get_videos(author_id, poll.updated_at)
        if not widget_videos:
            return True

        if widget_videos:
            poll.updated_at = max(video.created_at for video in widget_videos)

        widget_video_settings = await widget_video_settings_grpc_client.get_video_settings(author_id, ZERO_DATETIME)
        if widget_video_settings is None:
            return True

        _, queue_message, _ = await self.build_video_state_and_queue_messages(
            author_id,
            widget_videos=widget_videos,
            play_randomly=widget_video_settings.play_randomly,
        )
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
