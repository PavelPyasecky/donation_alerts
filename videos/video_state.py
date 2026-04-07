import datetime
import random
from collections.abc import Callable
from typing import Any, Literal

from redis.exceptions import WatchError

from configs.redis import get_redis_conn
from models.video_state import StoredWidgetVideoQueue, WidgetVideoQueue, WidgetVideoState
from models.videos import Video


class VideoStateService:
    REDIS_TRANSACTION_RETRIES = 5

    def __init__(self):
        self.redis_client = get_redis_conn()

    async def get_video_state(self, author_id: int) -> WidgetVideoState:
        key = self._get_video_state_key(author_id)
        state = await self.redis_client.get(key)
        if state:
            return WidgetVideoState.model_validate_json(state)
        return WidgetVideoState()

    async def get_stored_video_queue(self, author_id: int) -> StoredWidgetVideoQueue:
        key = self._get_video_queue_key(author_id)
        queue = await self.redis_client.get(key)
        if queue:
            return StoredWidgetVideoQueue.model_validate_json(queue)
        return StoredWidgetVideoQueue()

    async def get_video_queue(self, author_id: int, videos: list[Video]) -> WidgetVideoQueue:
        stored_queue = await self.get_stored_video_queue(author_id)
        return self._materialize_video_queue(stored_queue, videos)

    def _normalize_video_ids(self, video_ids: list[int]) -> list[int]:
        return list(dict.fromkeys(video_ids))

    def _get_original_video_ids(self, videos: list[Video]) -> list[int]:
        return self._normalize_video_ids([video.id for video in videos])

    def _materialize_video_queue(
        self, stored_queue: StoredWidgetVideoQueue, original_videos: list[Video]
    ) -> WidgetVideoQueue:
        videos_by_id = {video.id: video for video in original_videos}
        ordered_videos = [videos_by_id[video_id] for video_id in stored_queue.video_ids if video_id in videos_by_id]
        return WidgetVideoQueue(
            original_video_ids=stored_queue.original_video_ids,
            video_ids=[video.id for video in ordered_videos],
            play_randomly=stored_queue.play_randomly,
            version=stored_queue.version,
            updated_at=stored_queue.updated_at,
            videos=ordered_videos,
        )

    def _get_video_state_key(self, author_id: int) -> str:
        return f"widget_video_state:{author_id}"

    def _get_video_queue_key(self, author_id: int) -> str:
        return f"widget_video_queue:{author_id}"

    def _move_current_video_to_front(self, video_ids: list[int], current_video_id: int | None) -> list[int]:
        normalized_video_ids = self._normalize_video_ids(video_ids)
        if current_video_id is None or current_video_id not in normalized_video_ids:
            return normalized_video_ids
        return [current_video_id, *(video_id for video_id in normalized_video_ids if video_id != current_video_id)]

    def _rotate_queue_to_start_with(self, video_ids: list[int], start_video_id: int | None) -> list[int]:
        normalized_video_ids = self._normalize_video_ids(video_ids)
        if start_video_id is None or start_video_id not in normalized_video_ids:
            return normalized_video_ids

        start_index = normalized_video_ids.index(start_video_id)
        return normalized_video_ids[start_index:] + normalized_video_ids[:start_index]

    def _move_video_to_end(self, video_ids: list[int], video_id: int | None) -> list[int]:
        normalized_video_ids = self._normalize_video_ids(video_ids)
        if video_id is None or video_id not in normalized_video_ids:
            return normalized_video_ids
        return [current_video_id for current_video_id in normalized_video_ids if current_video_id != video_id] + [video_id]

    def _get_queue_anchor_video_id(
        self,
        current_queue: StoredWidgetVideoQueue,
        original_video_ids: list[int],
        current_video_id: int | None,
    ) -> int | None:
        normalized_original_video_ids = self._normalize_video_ids(original_video_ids)

        if current_queue.video_ids:
            queue_head_video_id = current_queue.video_ids[0]
            if queue_head_video_id in normalized_original_video_ids:
                return queue_head_video_id

        if current_video_id in normalized_original_video_ids:
            return current_video_id

        return None

    def _merge_queue_with_original_order(self, queue_video_ids: list[int], original_video_ids: list[int]) -> list[int]:
        normalized_original_video_ids = self._normalize_video_ids(original_video_ids)
        original_video_ids_set = set(normalized_original_video_ids)
        merged_queue = [
            video_id
            for video_id in self._normalize_video_ids(queue_video_ids)
            if video_id in original_video_ids_set
        ]
        merged_queue.extend(video_id for video_id in normalized_original_video_ids if video_id not in merged_queue)
        return merged_queue

    def _shuffle_queue(self, video_ids: list[int], current_video_id: int | None) -> list[int]:
        ordered_video_ids = self._move_current_video_to_front(video_ids, current_video_id)
        if not ordered_video_ids:
            return []

        if current_video_id is not None and ordered_video_ids[0] == current_video_id:
            head = ordered_video_ids[:1]
            tail = ordered_video_ids[1:]
            random.shuffle(tail)
            return [*head, *tail]

        random.shuffle(ordered_video_ids)
        return ordered_video_ids

    def _sanitize_state(self, current_state: WidgetVideoState, original_video_ids: list[int]) -> WidgetVideoState:
        if current_state.current_video_id in set(original_video_ids):
            return current_state

        if current_state.current_video_id is None:
            return current_state

        return current_state.model_copy(
            update={
                "current_video_id": None,
                "status": "idle",
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        )

    def _build_stored_queue(
        self,
        current_queue: StoredWidgetVideoQueue,
        original_video_ids: list[int],
        queue_video_ids: list[int],
        play_randomly: bool,
        updated_at: datetime.datetime,
    ) -> StoredWidgetVideoQueue:
        normalized_original_video_ids = self._normalize_video_ids(original_video_ids)
        normalized_queue_video_ids = self._merge_queue_with_original_order(
            queue_video_ids,
            normalized_original_video_ids,
        )

        if (
            current_queue.original_video_ids == normalized_original_video_ids
            and current_queue.video_ids == normalized_queue_video_ids
            and current_queue.play_randomly == play_randomly
        ):
            return current_queue

        next_version = current_queue.version + 1 if current_queue.version else 1
        return StoredWidgetVideoQueue(
            original_video_ids=normalized_original_video_ids,
            video_ids=normalized_queue_video_ids,
            play_randomly=play_randomly,
            version=next_version,
            updated_at=updated_at,
        )

    def _build_queue_after_original_videos_change(
        self,
        current_queue: StoredWidgetVideoQueue,
        original_video_ids: list[int],
        current_video_id: int | None,
    ) -> list[int]:
        normalized_original_video_ids = self._normalize_video_ids(original_video_ids)
        if current_queue.original_video_ids == normalized_original_video_ids:
            return self._merge_queue_with_original_order(current_queue.video_ids, normalized_original_video_ids)

        queue_anchor_video_id = self._get_queue_anchor_video_id(
            current_queue=current_queue,
            original_video_ids=normalized_original_video_ids,
            current_video_id=current_video_id,
        )

        if current_queue.play_randomly:
            next_queue_video_ids = self._merge_queue_with_original_order(
                current_queue.video_ids,
                normalized_original_video_ids,
            )

            return self._move_current_video_to_front(next_queue_video_ids, queue_anchor_video_id)

        return self._rotate_queue_to_start_with(normalized_original_video_ids, queue_anchor_video_id)

    def _build_queue_after_play_randomly_change(
        self,
        current_queue: StoredWidgetVideoQueue,
        original_video_ids: list[int],
        current_video_id: int | None,
        play_randomly: bool,
    ) -> list[int]:
        effective_original_video_ids = self._merge_queue_with_original_order(
            current_queue.original_video_ids,
            original_video_ids,
        )
        if not effective_original_video_ids:
            effective_original_video_ids = self._normalize_video_ids(original_video_ids)

        queue_anchor_video_id = self._get_queue_anchor_video_id(
            current_queue=current_queue,
            original_video_ids=effective_original_video_ids,
            current_video_id=current_video_id,
        )

        if play_randomly:
            return self._shuffle_queue(effective_original_video_ids, queue_anchor_video_id)

        return self._rotate_queue_to_start_with(effective_original_video_ids, queue_anchor_video_id)

    async def _run_transaction(
        self,
        author_id: int,
        updater: Callable[
            [WidgetVideoState, StoredWidgetVideoQueue],
            tuple[WidgetVideoState, StoredWidgetVideoQueue, Any],
        ],
    ):
        state_key = self._get_video_state_key(author_id)
        queue_key = self._get_video_queue_key(author_id)

        for _ in range(self.REDIS_TRANSACTION_RETRIES):
            async with self.redis_client.pipeline() as pipe:
                try:
                    await pipe.watch(state_key, queue_key)
                    raw_state = await pipe.get(state_key)
                    raw_queue = await pipe.get(queue_key)

                    current_state = WidgetVideoState.model_validate_json(raw_state) if raw_state else WidgetVideoState()
                    current_queue = (
                        StoredWidgetVideoQueue.model_validate_json(raw_queue) if raw_queue else StoredWidgetVideoQueue()
                    )

                    next_state, next_queue, result = updater(current_state, current_queue)
                    if next_state == current_state and next_queue == current_queue:
                        await pipe.unwatch()
                        return result

                    pipe.multi()
                    pipe.set(state_key, next_state.model_dump_json())
                    pipe.set(queue_key, next_queue.model_dump_json())
                    await pipe.execute()
                    return result
                except WatchError:
                    continue

        raise RuntimeError(f"Failed to update video state and queue for author_id={author_id}")

    async def sync_queue_with_original_videos(
        self,
        author_id: int,
        original_videos: list[Video],
    ) -> tuple[WidgetVideoState, WidgetVideoQueue]:
        original_video_ids = self._get_original_video_ids(original_videos)

        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = self._sanitize_state(current_state, original_video_ids)
            next_queue_video_ids = self._build_queue_after_original_videos_change(
                current_queue,
                original_video_ids,
                next_state.current_video_id,
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            next_queue = self._build_stored_queue(
                current_queue=current_queue,
                original_video_ids=original_video_ids,
                queue_video_ids=next_queue_video_ids,
                play_randomly=current_queue.play_randomly,
                updated_at=now,
            )
            materialized_queue = self._materialize_video_queue(next_queue, original_videos)
            return next_state, next_queue, (next_state, materialized_queue)

        return await self._run_transaction(author_id, updater)

    async def sync_queue_with_play_randomly(
        self,
        author_id: int,
        original_videos: list[Video],
        play_randomly: bool,
    ) -> tuple[WidgetVideoState, WidgetVideoQueue]:
        incoming_original_video_ids = self._get_original_video_ids(original_videos)

        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            effective_original_video_ids = self._merge_queue_with_original_order(
                current_queue.original_video_ids,
                incoming_original_video_ids,
            )
            if not effective_original_video_ids:
                effective_original_video_ids = incoming_original_video_ids

            next_state = self._sanitize_state(current_state, effective_original_video_ids)
            next_queue_video_ids = self._build_queue_after_play_randomly_change(
                current_queue=current_queue,
                original_video_ids=effective_original_video_ids,
                current_video_id=next_state.current_video_id,
                play_randomly=play_randomly,
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            next_queue = self._build_stored_queue(
                current_queue=current_queue,
                original_video_ids=effective_original_video_ids,
                queue_video_ids=next_queue_video_ids,
                play_randomly=play_randomly,
                updated_at=now,
            )
            materialized_queue = self._materialize_video_queue(next_queue, original_videos)
            return next_state, next_queue, (next_state, materialized_queue)

        return await self._run_transaction(author_id, updater)

    async def reorder_video_queue(
        self,
        author_id: int,
        requested_queue: WidgetVideoQueue,
        original_videos: list[Video],
    ) -> WidgetVideoQueue | None:
        original_video_ids = self._get_original_video_ids(original_videos)

        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = self._sanitize_state(current_state, original_video_ids)
            synced_queue_video_ids = self._build_queue_after_original_videos_change(
                current_queue=current_queue,
                original_video_ids=original_video_ids,
                current_video_id=next_state.current_video_id,
            )
            effective_current_queue = self._build_stored_queue(
                current_queue=current_queue,
                original_video_ids=original_video_ids,
                queue_video_ids=synced_queue_video_ids,
                play_randomly=current_queue.play_randomly,
                updated_at=current_queue.updated_at,
            )

            normalized_requested_video_ids = self._normalize_video_ids(requested_queue.video_ids)
            current_video_ids = effective_current_queue.video_ids
            requested_version = requested_queue.version if requested_queue.version > 0 else None
            if requested_version is not None and requested_version != effective_current_queue.version:
                return next_state, effective_current_queue, None
            if (
                len(normalized_requested_video_ids) != len(current_video_ids)
                or set(normalized_requested_video_ids) != set(current_video_ids)
            ):
                return next_state, effective_current_queue, None

            next_queue = self._build_stored_queue(
                current_queue=effective_current_queue,
                original_video_ids=original_video_ids,
                queue_video_ids=normalized_requested_video_ids,
                play_randomly=effective_current_queue.play_randomly,
                updated_at=datetime.datetime.now(datetime.timezone.utc),
            )
            return next_state, next_queue, self._materialize_video_queue(next_queue, original_videos)

        return await self._run_transaction(author_id, updater)
    
    async def play(self, author_id: int, video_id: int, source: Literal["widget", "donators"]) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "current_video_id": video_id,
                    "video_source": source,
                    "status": "playing",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state
    
    async def pause(self, author_id: int) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "status": "paused",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state
    
    async def idle(self, author_id: int) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "current_video_id": None,
                    "video_source": None,
                    "status": "idle",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state

    async def disable_video(self, author_id: int) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "video_disabled": True,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state

    async def enable_video(self, author_id: int) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "video_disabled": False,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state

    async def set_volume(self, author_id: int, volume: int) -> WidgetVideoState:
        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = current_state.model_copy(
                update={
                    "volume": volume,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            )
            return next_state, current_queue, next_state

        next_state = await self._run_transaction(author_id, updater)
        return next_state

    async def skip(
        self,
        author_id: int,
        original_videos: list[Video],
        source: Literal["widget", "donators"] | None = None,
    ) -> tuple[WidgetVideoState, WidgetVideoQueue | None]:
        original_video_ids = self._get_original_video_ids(original_videos)

        def updater(current_state: WidgetVideoState, current_queue: StoredWidgetVideoQueue):
            next_state = self._sanitize_state(current_state, original_video_ids)
            next_queue_video_ids = self._build_queue_after_original_videos_change(
                current_queue=current_queue,
                original_video_ids=original_video_ids,
                current_video_id=next_state.current_video_id,
            )

            should_update_queue = source == "widget"
            if should_update_queue:
                current_queue_head_video_id = next_queue_video_ids[0] if next_queue_video_ids else None
                next_queue_video_ids = self._move_video_to_end(next_queue_video_ids, current_queue_head_video_id)

            next_queue = self._build_stored_queue(
                current_queue=current_queue,
                original_video_ids=original_video_ids,
                queue_video_ids=next_queue_video_ids,
                play_randomly=current_queue.play_randomly,
                updated_at=datetime.datetime.now(datetime.timezone.utc),
            )
            queue_payload = self._materialize_video_queue(next_queue, original_videos) if should_update_queue else None
            return next_state, next_queue, (next_state, queue_payload)

        return await self._run_transaction(author_id, updater)



video_state_service = VideoStateService()
