from redis.asyncio import Redis

from configs import config


def get_user_state_redis_conn():
    return Redis(
        username=config.USER_STATE_REDIS_USER,
        password=config.USER_STATE_REDIS_PASSWORD,
        host=config.USER_STATE_REDIS_HOST,
        port=config.USER_STATE_REDIS_PORT,
        db=config.USER_STATE_REDIS_DB,
    )

def get_redis_conn():
    return Redis(
        username=config.REDIS_USER,
        password=config.REDIS_PASSWORD,
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
    )
