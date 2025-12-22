from __future__ import annotations

from pydantic import BaseModel, Field


class Settings(BaseModel):
    VIZIONER_BROKER_URL: str = Field("redis://tasker:6379/0", description="Celery broker URL")
    VIZIONER_REDIS_URL: str = Field("redis://tasker:6379/0", description="Redis URL")
    VIZIONER_CONTENT_BUCKET: str = Field("vizioner", description="Content bucket")
    VIZIONER_CONTENT_TTL: int = Field(3600, description="Content TTL in seconds")
    VIZIONER_WORKER_NUMBER: int = Field(1, description="Worker concurrency")

    class Config:
        env_file = ".env"
        validate_assignment = True
