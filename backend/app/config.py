import json

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AIERP"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    APP_ENV: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "aierp"
    DB_PASSWORD: str = ""
    DB_NAME: str = "aierp"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_POOL_PRE_PING: bool = True
    SLOW_QUERY_THRESHOLD_MS: int = 500

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.siliconflow.cn/v1"
    AI_MODEL: str = "deepseek-ai/DeepSeek-V4-Flash"
    AI_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V4-Flash"
    AI_FOLLOWUP_MODEL: str = ""
    AI_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    CORS_ORIGINS: list[str] = ["http://localhost:3002", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [
                            str(item).strip() for item in parsed if str(item).strip()
                        ]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(value, (tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        if self.APP_ENV == "production":
            if not self.DB_PASSWORD:
                raise ValueError("DB_PASSWORD must be set in production")
            if not self.JWT_SECRET:
                raise ValueError("JWT_SECRET must be set in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must be set in production")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
        return self

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
