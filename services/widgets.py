import jwt
import logging

from fastapi import HTTPException, status

from configs.redis import get_user_state_redis_conn
from models.widget_token import WidgetTokenInfo
from utils.jwt import decode_custom_jwt


async def parse_widget_token(token: str) -> WidgetTokenInfo:
    try:
        token_info = decode_custom_jwt(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid widget_token")

    conn = get_user_state_redis_conn()

    cache_key = f"streamer:{token_info.author_id}:widget_control"
    value = await conn.get(cache_key)
    if value is None:
        logging.warning(f"Widget control uuid for author {token_info.author_id} not exists")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid widget_token")

    control_uuid = value.decode()

    if control_uuid is None or control_uuid != token_info.control_uuid:
        logging.warning(f"Widget control uuid for author {token_info.author_id} incorrect")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid widget_token")

    return token_info
