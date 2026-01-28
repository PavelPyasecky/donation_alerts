import asyncio
import json

from asyncio import AbstractEventLoop
from aio_pika import connect_robust
from aio_pika.abc import AbstractExchange, AbstractChannel, AbstractQueue, AbstractRobustConnection, ExchangeType

from alerts.services import send_alert_to_author_service
from configs import config
from alerts.models import Alert


class RabbitMQConsumer:
    def __init__(self):
        self.channels: list[AbstractChannel] = []

    async def connect(self, url: str, loop: AbstractEventLoop):
        self.connection: AbstractRobustConnection = (
            await connect_robust(url, loop=loop)
        )

    async def close(self):
        for channel in self.channels:
            await channel.close()
        await self.connection.close()

    async def queue_iter(self, queue: AbstractQueue, exchange: AbstractExchange):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    alert = Alert(**data)
                    asyncio.create_task(send_alert_to_author_service(alert, exchange))
                    
    async def create_listener(self, author_id: int) -> AbstractExchange:
        channel = await self.connection.channel()
        self.channels.append(channel)

        exchange = await channel.declare_exchange(
            config.ALERTS_EXCHANGE, ExchangeType.DIRECT, durable=True
        )
        queue = await channel.declare_queue(
            str(author_id), durable=True, exclusive=False, auto_delete=False
        )
        statuses_queue = await channel.declare_queue(
            config.ALERT_STATUS_QUEUE, durable=True,
        )

        await queue.bind(exchange, routing_key=str(author_id))
        await statuses_queue.bind(exchange, routing_key=config.ALERT_STATUS_QUEUE)

        asyncio.create_task(self.queue_iter(queue, exchange))

        return exchange


rabbitmq_consumer = RabbitMQConsumer()
