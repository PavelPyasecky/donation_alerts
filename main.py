import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.ALLOWED_HOSTS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
