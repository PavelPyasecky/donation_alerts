import datetime

from configs.redis import get_redis_conn
from models.alert_state import WidgetAlertState


class AlertStateService:
    def __init__(self):
        self.redis_client = get_redis_conn()

    def _get_alert_state_key(self, author_id: int) -> str:
        return f"widget_alert_state:{author_id}"

    async def get_alert_state(self, author_id: int) -> WidgetAlertState:
        key = self._get_alert_state_key(author_id)
        state = await self.redis_client.get(key)
        if state:
            return WidgetAlertState.model_validate_json(state)
        return WidgetAlertState()

    async def set_alert_state(
        self,
        author_id: int,
        current_alert_id: int | None,
        start_viewing_at: datetime.datetime | None,
        current_donation_id: int | None,
    ) -> WidgetAlertState:
        next_state = WidgetAlertState(
            current_alert_id=current_alert_id,
            start_viewing_at=start_viewing_at,
            current_donation_id=current_donation_id,
        )
        await self.redis_client.set(self._get_alert_state_key(author_id), next_state.model_dump_json())
        return next_state


alert_state_service = AlertStateService()
