import os
from urllib.parse import urlparse

from dotenv import load_dotenv


dotenv_path = ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def getenv(name: str) -> str:
    env = os.getenv(name)

    if env is None:
        raise ValueError(f"{name} is None")
    return env


def _split_csv_env(name: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


def _normalize_host(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""

    if "://" in candidate:
        parsed = urlparse(candidate)
        return (parsed.hostname or "").strip()

    return candidate.split("/")[0].split(":")[0].strip()


def _build_allowed_hosts() -> list[str]:
    explicit_hosts = [_normalize_host(value) for value in _split_csv_env("ALLOWED_HOSTS")]
    explicit_hosts = [host for host in explicit_hosts if host]
    if explicit_hosts:
        return explicit_hosts

    derived_hosts = [
        _normalize_host(os.getenv("DOMAIN", "")),
        _normalize_host(os.getenv("API_DOMAIN", "")),
        _normalize_host(os.getenv("PUBLIC_IP", "")),
    ]
    derived_hosts = [host for host in derived_hosts if host]
    if derived_hosts:
        return list(dict.fromkeys([*derived_hosts, "localhost", "127.0.0.1"]))

    return ["*"]


# RABITMQ
RMQ_URL = getenv("RMQ_URL")
ALERTS_EXCHANGE = getenv("ALERTS_EXCHANGE")
CAMPAIGNS_EXCHANGE = getenv("CAMPAIGNS_EXCHANGE")
ALERT_STATUS_QUEUE = getenv("ALERT_STATUS_QUEUE")
WIDGET_TOKEN_SECRET = getenv("WIDGET_TOKEN_SECRET")

GET_ALET_SETTINGS_INTERVAL = int(getenv("GET_ALET_SETTINGS_INTERVAL"))

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


ALLOWED_HOSTS = _build_allowed_hosts()


CORS_ALLOWED_ORIGINS = [
    url.strip()
    for url in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if url.strip()
]
