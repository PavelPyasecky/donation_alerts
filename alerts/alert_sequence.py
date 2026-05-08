import json

from pydantic import BaseModel, Field

from configs.redis import get_redis_conn
from models.alert import Alert


class AlertSequenceItem(BaseModel):
    alert_id: int
    donation_id: int | None = Field(None)
    alert: Alert | None = Field(None)


class AlertSequenceService:
    def __init__(self):
        self.redis_client = get_redis_conn()

    def _get_sequence_key(self, author_id: int) -> str:
        return f"widget_alert_sequence:{author_id}"

    async def set_alerts(self, author_id: int, alerts: list[Alert]) -> list[AlertSequenceItem]:
        sequence = self._deduplicate([self._make_item(alert) for alert in alerts])
        await self._set_sequence(author_id, sequence)
        return sequence

    async def add_alert(self, author_id: int, alert: Alert) -> list[AlertSequenceItem]:
        sequence = await self.get_sequence(author_id)
        sequence.append(self._make_item(alert))
        sequence = self._deduplicate(sequence)
        await self._set_sequence(author_id, sequence)
        return sequence

    async def advance_past(
        self,
        author_id: int,
        alert_id: int,
        donation_id: int | None,
    ) -> AlertSequenceItem | None:
        sequence = await self.get_sequence(author_id)
        current_index = self._find_index(sequence, alert_id, donation_id)
        if current_index is None:
            sequence = [
                item for item in sequence if not self._is_item_match(item, alert_id, donation_id)
            ]
        else:
            sequence = sequence[current_index + 1 :]
        await self._set_sequence(author_id, sequence)
        return sequence[0] if sequence else None

    async def get_sequence(self, author_id: int) -> list[AlertSequenceItem]:
        state = await self.redis_client.get(self._get_sequence_key(author_id))
        if not state:
            return []
        return [AlertSequenceItem.model_validate(item) for item in json.loads(state)]

    async def get_item(
        self,
        author_id: int,
        alert_id: int,
        donation_id: int | None,
    ) -> AlertSequenceItem | None:
        sequence = await self.get_sequence(author_id)
        current_index = self._find_index(sequence, alert_id, donation_id)
        if current_index is None:
            return None
        return sequence[current_index]

    async def clear_sequence(self, author_id: int) -> None:
        await self.redis_client.delete(self._get_sequence_key(author_id))

    async def _set_sequence(self, author_id: int, sequence: list[AlertSequenceItem]) -> None:
        await self.redis_client.set(
            self._get_sequence_key(author_id),
            json.dumps([item.model_dump(mode="json") for item in sequence]),
        )

    @staticmethod
    def _make_item(alert: Alert) -> AlertSequenceItem:
        return AlertSequenceItem(alert_id=alert.id, donation_id=alert.donation_id, alert=alert)

    @staticmethod
    def _deduplicate(sequence: list[AlertSequenceItem]) -> list[AlertSequenceItem]:
        result: list[AlertSequenceItem] = []
        seen: set[tuple[int, int | None]] = set()
        for item in sequence:
            identity = (item.alert_id, item.donation_id)
            if identity in seen or any(
                AlertSequenceService._is_item_match(stored_item, item.alert_id, item.donation_id)
                for stored_item in result
            ):
                continue
            seen.add(identity)
            result.append(item)
        return result

    @staticmethod
    def _find_index(
        sequence: list[AlertSequenceItem],
        alert_id: int,
        donation_id: int | None,
    ) -> int | None:
        for index, item in enumerate(sequence):
            if AlertSequenceService._is_item_match(item, alert_id, donation_id):
                return index
        return None

    @staticmethod
    def _is_item_match(
        item: AlertSequenceItem,
        alert_id: int,
        donation_id: int | None,
    ) -> bool:
        return item.alert_id == alert_id or (
            donation_id is not None and item.donation_id == donation_id
        )


alert_sequence_service = AlertSequenceService()
