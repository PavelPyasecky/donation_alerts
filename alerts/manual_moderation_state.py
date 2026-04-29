import json
from decimal import Decimal, InvalidOperation

from configs.redis import get_redis_conn
from models.alert import Alert
from models.settings import ModerationSettings


class ManualModerationStateService:
    def __init__(self):
        self.redis_client = get_redis_conn()

    def _get_alerts_key(self, author_id: int) -> str:
        return f"manual_moderation_alerts:{author_id}"

    async def get_alert_ids(self, author_id: int) -> list[int]:
        state = await self.redis_client.get(self._get_alerts_key(author_id))
        if not state:
            return []
        return [self._parse_stored_id(alert_id) for alert_id in json.loads(state)]

    async def set_alert_ids(self, author_id: int, alert_ids: list[int]) -> list[int]:
        await self.redis_client.set(
            self._get_alerts_key(author_id),
            json.dumps(alert_ids),
        )
        return alert_ids

    async def add_alert(self, author_id: int, alert: Alert) -> list[int]:
        alert_ids = await self.get_alert_ids(author_id)
        alert_id = self._get_alert_id(alert)
        if alert_id in alert_ids:
            return alert_ids
        alert_ids.append(alert_id)
        return await self.set_alert_ids(author_id, alert_ids)

    async def add_alerts(self, author_id: int, new_alerts: list[Alert]) -> list[int]:
        alert_ids = await self.get_alert_ids(author_id)
        for alert in new_alerts:
            alert_id = self._get_alert_id(alert)
            if alert_id not in alert_ids:
                alert_ids.append(alert_id)
        return await self.set_alert_ids(author_id, alert_ids)

    async def remove_alert(
        self,
        author_id: int,
        alert_id: int,
    ) -> list[int]:
        alert_ids = await self.get_alert_ids(author_id)
        alert_ids = [stored_alert_id for stored_alert_id in alert_ids if stored_alert_id != alert_id]
        return await self.set_alert_ids(author_id, alert_ids)

    @staticmethod
    def should_moderate_manually(settings: ModerationSettings | None, alert: Alert) -> bool:
        if settings is None or not settings.is_active or not settings.is_manual:
            return False

        activation_amount = ManualModerationStateService._parse_amount(settings.activation_amount)
        if activation_amount is None:
            return False

        alert_amount = ManualModerationStateService._parse_amount(alert.amount)
        if alert_amount is None:
            return False

        return alert_amount < activation_amount

    @staticmethod
    def _get_alert_id(alert: Alert) -> int:
        return alert.donation_id or alert.id

    @staticmethod
    def _parse_stored_id(alert_id: int | str | dict) -> int:
        if isinstance(alert_id, dict):
            alert_id = alert_id.get("donation_id") or alert_id["id"]
        return int(alert_id)

    @staticmethod
    def _parse_amount(amount: str | int | float | Decimal | None) -> Decimal | None:
        if amount in (None, ""):
            return Decimal("0")
        try:
            return Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return None


manual_moderation_state_service = ManualModerationStateService()
