from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ASD Edge AI Local Receiver"
    database_url: str = "sqlite:///./storage/asd_edge_ai.db"
    raw_storage_dir: str = "./storage/raw"
    cors_origins: str = "http://localhost:5173"
    device_registry_file: Path = Path("./storage/local/device-registry.json")
    operator_token: SecretStr = SecretStr("")
    cookie_secret: SecretStr = SecretStr("")
    cookie_secure: bool = True
    allow_insecure_local: bool = False
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = Field(default=8883, ge=1, le=65535)
    mqtt_username: str = "backend"
    mqtt_password: SecretStr = SecretStr("")
    mqtt_ca_file: str | None = None
    mqtt_client_id: str = "asd-ease-backend"
    mqtt_queue_messages: int = Field(default=256, ge=1, le=256)
    mqtt_queue_bytes: int = Field(default=1048576, ge=4096, le=1048576)
    command_timeout_seconds: int = Field(default=30, ge=1, le=30)
    drain_timeout_seconds: int = Field(default=30, ge=1, le=30)
    mqtt_lock_file: Path = Path("./storage/mqtt-receiver.lock")

    @model_validator(mode="after")
    def credentials_and_tls(self):
        for secret in (self.operator_token, self.cookie_secret):
            if len(secret.get_secret_value()) < 32:
                raise ValueError("Cần OPERATOR_TOKEN và COOKIE_SECRET riêng, ít nhất32 ký tự")
        if self.operator_token == self.cookie_secret:
            raise ValueError("Không dùng chung hai secret")
        if not self.cookie_secure and not self.allow_insecure_local:
            raise ValueError("Cookie HTTP chỉ dùng khi ALLOW_INSECURE_LOCAL=true")
        if self.mqtt_enabled:
            if not self.mqtt_password.get_secret_value():
                raise ValueError("Cần mật khẩu MQTT backend")
            if not self.mqtt_ca_file and not self.allow_insecure_local:
                raise ValueError("Cần MQTT_CA_FILE hoặc ngoại lệ LAN phát triển")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

