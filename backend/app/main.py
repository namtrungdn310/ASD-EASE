from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import annotations, auth, device_control, devices, events, health, raw_data, sessions, telemetry, websocket
from app.core.config import get_settings
from app.db.database import SessionLocal, engine
from app.db.migrations import upgrade
from app.core.security import Registry
from app.services.mqtt_runtime import MQTTRuntime
from pathlib import Path
import logging


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.settings = settings
    application.state.registry = Registry(settings.device_registry_file)
    for identity in application.state.registry.entries:
        if identity.mqtt_username == settings.mqtt_username or identity.http_token in {settings.operator_token, settings.cookie_secret}:
            raise ValueError("Thiết bị phải có tài khoản/token riêng, không dùng credential backend/người vận hành")
    if engine.url.database and engine.url.database != ":memory:":
        Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    backup = upgrade(engine)
    if backup:
        logging.getLogger(__name__).warning("Đã sao lưu DB trước migration: %s", backup)
    runtime = MQTTRuntime(settings, application.state.registry, SessionLocal)
    application.state.mqtt = runtime
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()
        engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)
for router in (health.router, auth.router, device_control.router, telemetry.router, raw_data.router, devices.router, sessions.router, annotations.router, events.router, websocket.router):
    app.include_router(router, prefix="/api/v1")

