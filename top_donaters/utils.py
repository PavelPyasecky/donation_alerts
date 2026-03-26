import datetime
import uuid
from decimal import Decimal, InvalidOperation

from models.top_donaters import DonationEvent
from models.widget_message import WidgetMessage


def _to_decimal(value: str | float | int | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _ensure_datetime(value: datetime.datetime | str | None) -> datetime.datetime:
    parsed = _parse_datetime(value)
    return parsed or datetime.datetime.now(datetime.timezone.utc)


def _parse_datetime(value: datetime.datetime | str | None) -> datetime.datetime | None:
    if value is None:
        return None
    value = _decode(value)
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    try:
        parsed = datetime.datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _period_seconds(period: str) -> int | None:
    match period:
        case "all_time":
            return None
        case "last_month":
            return 30 * 24 * 60 * 60
        case "last_week":
            return 7 * 24 * 60 * 60
        case "last_day":
            return 24 * 60 * 60
        case _:
            return 24 * 60 * 60


def _extract_donations(message: WidgetMessage) -> list[DonationEvent]:
    if message.action == "test_alert":
        return []

    payloads = message.data if isinstance(message.data, list) else [message.data]
    result: list[DonationEvent] = []

    for payload in payloads:
        donation = _payload_to_donation(payload)
        if donation:
            result.append(donation)

    return result


def _payload_to_donation(payload: object) -> DonationEvent | None:
    donor_name = getattr(payload, "donor_name", None)
    amount = getattr(payload, "amount", None)
    if donor_name is None or amount is None:
        return None

    created_at = getattr(payload, "timestamp", None) or getattr(payload, "created_at", None)
    donation_id = getattr(payload, "donation_id", None) or getattr(payload, "id", None)
    if donation_id is None:
        donation_id = uuid.uuid4().hex

    return DonationEvent(
        donor_name=donor_name,
        amount=_to_decimal(amount),
        created_at=_ensure_datetime(created_at),
        donation_id=str(donation_id),
    )


def _decode(value: object) -> object:
    if isinstance(value, bytes):
        return value.decode()
    return value
