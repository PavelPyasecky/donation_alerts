import jwt

from configs import config
from models.widget_token import WidgetTokenInfo


def decode_custom_jwt(token: str) -> WidgetTokenInfo:
    secret_key = config.WIDGET_TOKEN_SECRET
    algorithm = "HS256"

    payload = jwt.decode(token, secret_key, algorithms=[algorithm])

    return WidgetTokenInfo(**payload)
