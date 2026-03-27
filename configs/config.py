import os

from dotenv import load_dotenv

dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def getenv(name: str, default=None) -> str:
    env = os.getenv(name)

    if env is None:
        if default is None:
            raise ValueError(f"{name} is None")
        else:
            return default
    return env


# RABITMQ
RMQ_URL = getenv("RMQ_URL")
ALERTS_EXCHANGE = getenv("ALERTS_EXCHANGE")
CAMPAIGNS_EXCHANGE = getenv("CAMPAIGNS_EXCHANGE")
ALERT_STATUS_QUEUE = getenv("ALERT_STATUS_QUEUE")
WIDGET_TOKEN_SECRET = getenv("WIDGET_TOKEN_SECRET")

CHECK_NEW_ALET_SETTINGS_INTERVAL = int(getenv("CHECK_NEW_ALET_SETTINGS_INTERVAL", 10))
CHECK_NEW_BAN_WORDS_INTERVAL = int(getenv("CHECK_NEW_BAN_WORDS_INTERVAL", 30))
CHECK_NEW_MODERATION_SETTINGS_INTERVAL = int(getenv("CHECK_NEW_MODERATION_SETTINGS_INTERVAL", 60))

CLEAN_UP_TASKS_INTERVAL = int(getenv("CLEAN_UP_TASKS_INTERVAL", 60))

REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = getenv("REDIS_PORT")
REDIS_DB = getenv("REDIS_DB")

USER_STATE_REDIS_USER = os.getenv("USER_STATE_REDIS_USER")
USER_STATE_REDIS_PASSWORD = os.getenv("USER_STATE_REDIS_PASSWORD")
USER_STATE_REDIS_HOST = getenv("USER_STATE_REDIS_HOST")
USER_STATE_REDIS_PORT = getenv("USER_STATE_REDIS_PORT")
USER_STATE_REDIS_DB = getenv("USER_STATE_REDIS_DB")

GRPC_SERVER_URL = getenv("GRPC_SERVER_URL")


ALLOWED_HOSTS = [url.strip() for url in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if url.strip()]


CORS_ALLOWED_ORIGINS = [
    url.strip() for url in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if url.strip()
]
