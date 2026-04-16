import datetime
import json
import logging

from aio_pika.abc import AbstractIncomingMessage

from configs.constants import NOW
from configs.redis import get_redis_conn
from models.donations import Donater
from models.settings import StatisticWidgetSettings
from models.widget_message import WidgetMessage, WidgetMessageTypes
from statistics_widget.cache import TopDonatersCache
from statistics_widget.grpc import donations_grpc_client, statistics_grpc_client
from statistics_widget.utils import _payload_to_donation, period_to_seconds, period_to_days
from utils.websocket_manager import WSManager


class StatisticWidgetWSManager(WSManager):
    def __init__(self):
        super().__init__()
        self._settings: dict[int, StatisticWidgetSettings] = {}
        self._cache = TopDonatersCache(get_redis_conn())

    def register_setting(self, author_id: int, setting: StatisticWidgetSettings) -> None:
        self._settings[author_id] = setting

    def unregister_setting(self, author_id: int) -> StatisticWidgetSettings | None:
        return self._settings.pop(author_id, None)

    def has_author_settings(self, author_id: int) -> bool:
        return bool(self._settings.get(author_id))

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
                logging.exception("Failed to parse statistics RMQ message")
                return True

            match message_model.type_:
                case WidgetMessageTypes.event:
                    match message_model.action:
                        case "new_donation":
                            donation = _payload_to_donation(message_model.data)
                            if donation is None:
                                logging.warning("Statistics RMQ message has invalid donation payload")
                                return True

                            setting = self._settings[author_id]

                            match setting.type:
                                case "top_donators":
                                    await self._cache.record_donation(
                                        author_id, setting.period, donation, period_to_seconds(setting.period)
                                    )
                                    await self._broadcast_statistics(author_id, setting)
                                case "last_donations":
                                    await self.broadcast(
                                        author_id, message_model.model_dump(mode="json", by_alias=True)
                                    )
                            return True

        return _on_rmq_message

    async def broadcast_widget_settings(self, ws_key: any, author_id: int, setting_id: int) -> None:
        if not self.is_author_connected(ws_key):
            return False

        setting = self._settings[author_id]

        widget_settings = await statistics_grpc_client.get_statistic_widget_settings(
            author_id, setting_id, setting.updated_at
        )
        if widget_settings is None:
            return True

        should_rebuild_list = (
            setting.type != widget_settings.type
            or setting.elements_count != widget_settings.elements_count
            or setting.period != widget_settings.period
        )

        self.register_setting(author_id, widget_settings)
        message = WidgetMessage.make_statistic_widget_settings_message(widget_settings)
        await self.broadcast(ws_key, message.model_dump(mode="json", by_alias=True))

        if should_rebuild_list:
            await self.first_broadcast_by_type(author_id, widget_settings)

        return True
    
    async def first_broadcast_by_type(self, author_id: int, setting: StatisticWidgetSettings) -> None:
        match setting.type:
            case "top_donators":
                await self._broadcast_grpc_statistics(author_id, setting)
            case "last_donations":
                await self._broadcast_last_donations(author_id, setting)

    async def _broadcast_grpc_statistics(self, author_id: int, setting: StatisticWidgetSettings) -> None:
        time_now = NOW()
        period_days = period_to_days(setting.period)

        start_time = time_now - datetime.timedelta(days=period_days)
        union_by_donor_names_list = await donations_grpc_client.get_union_by_donor_names_list(
            author_id,
            start_time,
            time_now,
            setting.elements_count,
        )
        message = WidgetMessage.make_union_by_donor_names_list_message(union_by_donor_names_list)
        await self.broadcast(author_id, message.model_dump(mode="json", by_alias=True))

        await self.seed_cache_if_empty(author_id, setting.period, union_by_donor_names_list)

    async def _broadcast_statistics(self, author_id: int, setting: StatisticWidgetSettings) -> None:
        donaters = await self._cache.get_top(author_id, setting.period, setting.elements_count)
        message = WidgetMessage.make_union_by_donor_names_list_message(donaters)
        payload = message.model_dump(mode="json", by_alias=True)
        await self.broadcast(author_id, payload)

    async def _broadcast_last_donations(self, author_id: int, setting: StatisticWidgetSettings) -> None:
        donations = await donations_grpc_client.get_last_donations_list(author_id, setting.elements_count)
        message = WidgetMessage.make_last_donations_list_message(donations)
        payload = message.model_dump(mode="json", by_alias=True)
        await self.broadcast(author_id, payload)


ws_statistic_widget_manager = StatisticWidgetWSManager()
