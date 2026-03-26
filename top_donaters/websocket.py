import json
import logging

from aio_pika.abc import AbstractIncomingMessage

from configs.redis import get_redis_conn
from models.donations import Donater
from models.top_donaters import TopDonatersSettingInfo
from models.widget_message import WidgetMessage, WidgetMessageTypes
from top_donaters.cache import TopDonatersCache
from top_donaters.utils import _payload_to_donation, _period_seconds
from utils.websocket_manager import WSManager


class TopDonatersWSManager(WSManager):
    def __init__(self):
        super().__init__()
        self._settings: dict[int, TopDonatersSettingInfo] = {}
        self._author_settings: dict[int, set[int]] = {}
        self._cache = TopDonatersCache(get_redis_conn())

    def register_setting(self, setting_id: int, author_id: int, period: str, elements_count: int) -> None:
        self._settings[setting_id] = TopDonatersSettingInfo(
            setting_id=setting_id,
            author_id=author_id,
            period=period,
            elements_count=elements_count,
        )
        self._author_settings.setdefault(author_id, set()).add(setting_id)

    def unregister_setting(self, setting_id: int) -> int | None:
        info = self._settings.pop(setting_id, None)
        if not info:
            return None
        author_settings = self._author_settings.get(info.author_id)
        if author_settings:
            author_settings.discard(setting_id)
            if not author_settings:
                self._author_settings.pop(info.author_id, None)
                return info.author_id
        return None

    def has_author_settings(self, author_id: int) -> bool:
        return bool(self._author_settings.get(author_id))

    async def seed_cache_if_empty(self, author_id: int, period: str, donaters: list[Donater]) -> None:
        await self._cache.seed_from_list(author_id, period, donaters)

    def on_rmq_message(self, author_id: int):
        async def _on_rmq_message(message: AbstractIncomingMessage):
            if not self.has_author_settings(author_id):
                return False

            try:
                data = json.loads(message.body.decode())
                message_model = WidgetMessage(**data)
            except Exception:
                logging.exception("Failed to parse top donaters RMQ message")
                return True

            match message_model.type_:
                case WidgetMessageTypes.event:
                    match message_model.action:
                        case "new_donation":
                            donation = message_model.data

                            settings = self._get_settings_for_author(author_id)
                            periods = {setting.period for setting in settings}
                            for period in periods:
                                window_seconds = _period_seconds(period)
                                await self._cache.record_donation(author_id, period, donation, window_seconds)

                            await self._broadcast_updates(author_id, settings)
                            return True

        return _on_rmq_message

    async def _broadcast_updates(self, author_id: int, settings: list[TopDonatersSettingInfo]) -> None:
        if not settings:
            return

        for period in {setting.period for setting in settings}:
            period_settings = [setting for setting in settings if setting.period == period]
            max_limit = max(setting.elements_count for setting in period_settings)
            donaters = await self._cache.get_top(author_id, period, max_limit)
            message = WidgetMessage.make_union_by_donor_names_list_message(donaters)
            payload = message.model_dump(mode="json", by_alias=True)
            for setting in period_settings:
                await self.broadcast(setting.setting_id, payload)

    def _get_settings_for_author(self, author_id: int) -> list[TopDonatersSettingInfo]:
        setting_ids = self._author_settings.get(author_id, set())
        return [self._settings[setting_id] for setting_id in setting_ids if setting_id in self._settings]


ws_top_donaters_manager = TopDonatersWSManager()
