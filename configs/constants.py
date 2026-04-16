import datetime

ZERO_DATETIME = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
NOW = lambda: datetime.datetime.now(datetime.timezone.utc)
