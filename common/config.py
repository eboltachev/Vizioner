from __future__ import annotations

import os
from dataclasses import dataclass

from common.settings import Settings


@dataclass(frozen=True)
class State:
    broker_url: str
    redis_url: str
    content_bucket: str
    content_ttl: int
    worker_concurrency: int


def get_state() -> State:
    env_settings = Settings()
    broker_url = env_settings.VIZIONER_BROKER_URL
    redis_url = env_settings.VIZIONER_REDIS_URL or broker_url
    content_bucket = env_settings.VIZIONER_CONTENT_BUCKET
    content_ttl = env_settings.VIZIONER_CONTENT_TTL
    worker_concurrency = env_settings.VIZIONER_WORKER_NUMBER
    return State(
        broker_url=broker_url,
        redis_url=redis_url,
        content_bucket=content_bucket,
        content_ttl=content_ttl,
        worker_concurrency=worker_concurrency,
    )
