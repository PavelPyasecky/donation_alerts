from redis.asyncio import Redis

from configs import config


def get_redis_conn():
    return Redis(
        username=config.REDIS_USER,
        password=config.REDIS_PASSWORD,
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
    )
