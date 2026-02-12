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

REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = getenv("REDIS_PORT")
REDIS_DB = getenv("REDIS_DB")


ALLOWED_HOSTS = [
    url.strip()
    for url in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if url.strip()
]


CORS_ALLOWED_ORIGINS = [
    url.strip()
    for url in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if url.strip()
]
