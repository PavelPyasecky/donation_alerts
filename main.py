import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from alerts.rabbitmq_service import rabbitmq_consumer
from alerts.routers import router
from configs import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await rabbitmq_consumer.connect(config.RMQ_URL, loop)
    yield
    await rabbitmq_consumer.close()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
