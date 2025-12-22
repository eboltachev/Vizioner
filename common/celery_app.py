from __future__ import annotations

import os

from celery import Celery

from common.config import get_state

settings = get_state()

imports_env = os.getenv("VIZIONER_CELERY_IMPORTS", "")
imports = [value for value in (item.strip() for item in imports_env.split(",")) if value]

celery_app = Celery(
    "vizioner",
    broker=settings.broker_url,
    backend=settings.broker_url,
    include=imports or None,
)
celery_app.conf.update(
    task_track_started=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
)
