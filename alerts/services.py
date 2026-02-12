import asyncio
import datetime
import json
import jwt
import logging

from aio_pika import Message
from aio_pika.abc import AbstractExchange
from fastapi import WebSocketDisconnect

from alerts.websocket import ws_manager
from alerts.models import Alert, AlertStatus, Statuses, WidgetTokenInfo
from configs import config


async def send_alert_to_author_service(
    alert: Alert, exchange: AbstractExchange, current_attemp: int = 1
) -> AlertStatus:
    try:
        await ws_manager.send_to_author(alert.author_id, alert.model_dump(mode="json"))
    except WebSocketDisconnect as e:
        logging.error(f"Error when sending alert {alert.alert_id}: {e}")
        await asyncio.sleep(20)
        if current_attemp < 2:
            return await send_alert_to_author_service(
                alert, exchange, current_attemp + 1
            )
        else:
            status = AlertStatus(
                alert_id=alert.alert_id,
                status=Statuses.error,
                external_id=f"fastapi_alert_{alert.alert_id}",
                delivered_at=datetime.datetime.now(),
            )

            await exchange.publish(
                message=Message(body=status.model_dump_json().encode()),
                routing_key=config.ALERT_STATUS_QUEUE,
            )


def get_status_publisher(exchange: AbstractExchange):
    async def wrapper(status_data: dict):
        await exchange.publish(
            message=Message(body=json.dumps(status_data).encode()),
            routing_key=config.ALERT_STATUS_QUEUE,
        )
    
    return wrapper


def decode_custom_jwt(token: str) -> WidgetTokenInfo:
    secret_key = config.WIDGET_TOKEN_SECRET
    algorithm = 'HS256'

    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    
    return WidgetTokenInfo(**payload)
