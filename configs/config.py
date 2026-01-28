import os

from dotenv import load_dotenv


dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def getenv(name: str) -> str:
    env = os.getenv(name)

    if env is None:
        raise ValueError(f"{name} is None")
    return env


# RABITMQ
RMQ_URL = getenv("RMQ_URL")
ALERTS_EXCHANGE = getenv("ALERTS_EXCHANGE")
ALERT_STATUS_QUEUE = getenv("ALERT_STATUS_QUEUE")
