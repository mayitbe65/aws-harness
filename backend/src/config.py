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

    # Bedrock
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    VISION_API_TIMEOUT_SECONDS: int = 30

    # S3
    S3_BUCKET: str = "error-qa-frontend-1782299377"
    S3_PHOTO_PREFIX: str = "photos"

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
