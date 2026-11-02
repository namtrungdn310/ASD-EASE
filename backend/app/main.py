import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import annotations, devices, events, health, raw_data, sessions, telemetry, websocket
from app.core.config import get_settings
from app.db.database import Base, engine
from app.services.mqtt_subscriber import mqtt_subscriber


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    await mqtt_subscriber.start()
    yield
    await mqtt_subscriber.stop()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)
for router in (health.router, telemetry.router, raw_data.router, devices.router, sessions.router, annotations.router, events.router, websocket.router):
    app.include_router(router, prefix="/api/v1")
