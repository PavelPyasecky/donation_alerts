from aio_pika import connect_robust
from aio_pika.abc import ExchangeType, AbstractQueue


class RabbitMQ:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self, url: str):
        self.connection = await connect_robust(url)
        self.channel = await self.connection.channel()

    async def close(self):
        await self.connection.close()

    async def declare_queue(self, exchange_name: str, queue_name: str, routing_key: str | None = None):
        exchange = await self.channel.declare_exchange(exchange_name, ExchangeType.DIRECT, durable=True)
        queue = await self.channel.declare_queue(queue_name, durable=True, exclusive=False, auto_delete=False)
        await queue.bind(exchange, routing_key=routing_key or queue_name)
        return exchange, queue

    async def queue_iter(self, queue: AbstractQueue, action: callable):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    to_continue = await action(message)
                    if not to_continue:
                        break


rabbitmq = RabbitMQ()
