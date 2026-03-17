from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

from utils.rabbitmq import rabbitmq
from routers import widgets_router
from configs import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rabbitmq.connect(config.RMQ_URL)
    yield
    await rabbitmq.close()


app = FastAPI(lifespan=lifespan)
app.include_router(widgets_router)

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
