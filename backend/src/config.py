from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 1

    # Vision API
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str = "/path/to/credentials.json"
    VISION_API_TIMEOUT_SECONDS: int = 5

    # Admin 默认账号（生产环境请在 .env 中覆盖）
    ADMIN_EMAIL: str = "admin@school.edu"
    ADMIN_PASSWORD: str = "Admin123456!"
    ADMIN_NAME: str = "系统管理员"

    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]


settings = Settings()
