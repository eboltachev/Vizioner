from __future__ import annotations

import os
from dataclasses import dataclass

from common.settings import Settings


@dataclass(frozen=True)
class State:
    broker_url: str
    worker_concurrency: int
    worker_tempdir: str
    vizioner_content_internal_endpoint_url: str
    vizioner_content_public_endpoint_url: str
    vizioner_content_access_key: str
    vizioner_content_secret_key: str
    vizioner_content_bucket_name: str
    vizioner_content_region: str
    vizioner_content_ttl: int
    vizioner_content_certificate: bool
    vizioner_content_apply_public_policy: bool


def get_state() -> State:
    settings = Settings()
    return State(
        broker_url=settings.VIZIONER_BROKER_URL,
        worker_concurrency=settings.VIZIONER_WORKER_NUMBER,
        worker_tempdir=settings.VIZIONER_WORKER_TEMPDIR,
        vizioner_content_internal_endpoint_url=settings.VIZIONER_CONTENT_INTERNAL_ENDPOINT_URL,
        vizioner_content_public_endpoint_url=settings.VIZIONER_CONTENT_PUBLIC_ENDPOINT_URL,
        vizioner_content_access_key=settings.VIZIONER_CONTENT_ACCESS_KEY,
        vizioner_content_secret_key=settings.VIZIONER_CONTENT_SECRET_KEY,
        vizioner_content_bucket_name=settings.VIZIONER_CONTENT_BUCKET_NAME,
        vizioner_content_region=settings.VIZIONER_CONTENT_REGION,
        vizioner_content_ttl=settings.VIZIONER_CONTENT_TTL,
        vizioner_content_certificate=settings.VIZIONER_CONTENT_CERTIFICATE,
        vizioner_content_apply_public_policy=settings.VIZIONER_CONTENT_APPLY_PUBLIC_POLICY,
    )
