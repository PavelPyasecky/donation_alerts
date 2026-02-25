import asyncio

from asyncio import AbstractEventLoop
from aio_pika import connect_robust
from aio_pika.abc import AbstractExchange, AbstractChannel, AbstractRobustConnection, ExchangeType

from alerts.services import consumer_tasks_manager
from configs import config


class RabbitMQConsumer:
    def __init__(self):
        self.channels: list[AbstractChannel] = []
        self.author_iters: dict[int, asyncio.Task] = {}

    async def connect(self, url: str, loop: AbstractEventLoop):
        self.connection: AbstractRobustConnection = await connect_robust(url, loop=loop)

    async def close(self):
        for channel in self.channels:
            await channel.close()
        await self.connection.close()

    async def create_listener(self, author_id: int) -> AbstractExchange:
        channel = await self.connection.channel()
        self.channels.append(channel)

        exchange = await channel.declare_exchange(config.ALERTS_EXCHANGE, ExchangeType.DIRECT, durable=True)
        queue = await channel.declare_queue(str(author_id), durable=True, exclusive=False, auto_delete=False)
        statuses_queue = await channel.declare_queue(
            config.ALERT_STATUS_QUEUE,
            durable=True,
        )

        await queue.bind(exchange, routing_key=str(author_id))
        await statuses_queue.bind(exchange, routing_key=config.ALERT_STATUS_QUEUE)

        await consumer_tasks_manager.start_queue_iter(author_id, queue, exchange)

        return exchange


rabbitmq_consumer = RabbitMQConsumer()
