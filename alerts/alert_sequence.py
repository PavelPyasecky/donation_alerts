from pydantic import BaseModel, Field

from models.alert import Alert, AlertSetting, AlertSettingsGroup
from models.settings import ModerationSettings


class AlertSequenceData(BaseModel):
    moderation_settings: ModerationSettings | None = Field(None)
    connected_groups: list[AlertSettingsGroup] = Field(default_factory=list)

    def get_moderation_duration_seconds(self) -> int:
        return self.moderation_settings.duration if self.moderation_settings else 0
    
    def get_max_viewing_duration_seconds_by_amount(self, amount: str) -> int:
        if not self.connected_groups:
            return 0
        return max(group.get_max_viewing_duration_seconds_by_amount(amount) for group in self.connected_groups)


class AlertSequenceItem(BaseModel):
    alert_id: int
    donation_id: int | None = Field(None)
    amount: str


class AlertSequence(BaseModel):
    author_id: int
    items: list[AlertSequenceItem]
    moderation_settings: ModerationSettings | None = None
    max_donation_duration_seconds: int = 0


class AlertSequenceService:
    def __init__(self):
        self.alert_sequences: dict[int, list[AlertSequenceItem]] = {}
        self.alert_sequence_data: dict[int, AlertSequenceData] = {}

    def _get_sequence_key(self, author_id: int) -> str:
        return f"widget_alert_sequence:{author_id}"
    
    def set_alert_sequence_data(self, author_id: int, alert_sequence_data: AlertSequenceData) -> None:
        self.alert_sequence_data[author_id] = alert_sequence_data
    
    def get_alert_sequence_data(self, author_id: int) -> AlertSequenceData:
        return self.alert_sequence_data.get(author_id, AlertSequenceData())

    def set_alerts(self, author_id: int, alerts: list[Alert]) -> list[AlertSequenceItem]:
        if author_id not in self.alert_sequences:
            self.alert_sequences[author_id] = []
        self.alert_sequences[author_id].extend([self._make_item(alert) for alert in alerts])
        return self.alert_sequences[author_id]

    def add_alert(self, author_id: int, alert: Alert) -> list[AlertSequenceItem]:
        if author_id not in self.alert_sequences:
            self.alert_sequences[author_id] = []
        self.alert_sequences[author_id].append(self._make_item(alert))
    
    def get_first_sequence_item(self, author_id) -> AlertSequenceItem | None:
        return self.alert_sequences[author_id][0] if self.alert_sequences[author_id] else None
    
    def pop_first_sequence_item(self, author_id) -> AlertSequenceItem | None:
        return self.alert_sequences[author_id].pop(0) if self.alert_sequences[author_id] else None
    
    def clear_sequence(self, author_id: int) -> None:
        self.alert_sequences.pop(author_id)
    
    @staticmethod
    def _make_item(alert: Alert) -> AlertSequenceItem:
        return AlertSequenceItem(alert_id=alert.id, donation_id=alert.donation_id, amount=str(alert.amount))

alert_sequence_service = AlertSequenceService()
