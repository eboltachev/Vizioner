from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    @field_validator("VIZIONER_CONTENT_CERTIFICATE", mode="before")
    @classmethod
    def normalize_storage_cert(cls, value: str | bool) -> str | bool:
        if isinstance(value, str) and value.strip().lower() in {"false", "0", "no", ""}:
            return False
        return value

    VIZIONER_BROKER_URL: str = Field(default="redis://broker:6379/0", description="Celery broker URL")
    VIZIONER_WORKER_NUMBER: int = Field(default=1, description="Worker concurrency")
    VIZIONER_WORKER_TEMPDIR: str = Field(default="/tempfiles", description="Worker tempfiles")
    VIZIONER_CONTENT_INTERNAL_ENDPOINT_URL: str = Field(
        default="http://content:9000", description="S3 internal endpoint URL"
    )
    VIZIONER_CONTENT_PUBLIC_ENDPOINT_URL: str = Field(
        default="http://0.0.0.0:9000", description="S3 public endpoint URL"
    )
    VIZIONER_CONTENT_ACCESS_KEY: str = Field(default="minio_user", description="S3 access key")
    VIZIONER_CONTENT_SECRET_KEY: str = Field(None, description="S3 password")
    VIZIONER_CONTENT_BUCKET_NAME: str = Field(default="contents", description="S3 bucket name")
    VIZIONER_CONTENT_REGION: str = Field(default="us-east-1", description="S3 region")
    VIZIONER_CONTENT_TTL: int = Field(default=3600, description="S3 time to live")
    VIZIONER_CONTENT_CERTIFICATE: bool = Field(default=False, description="S3 certificate")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_assignment = True
        case_sensitive = False
        extra = "ignore"
