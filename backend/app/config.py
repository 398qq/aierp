from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AIERP"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    APP_ENV: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "aierp"
    DB_PASSWORD: str = "aierp"
    DB_NAME: str = "aierp"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "aierp-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.siliconflow.cn/v1"
    AI_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    AI_CHAT_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    AI_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    CORS_ORIGINS: list[str] = ["http://localhost:3002", "http://localhost:5173"]

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
