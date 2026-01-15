from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from botocore.exceptions import ClientError
from common.celery_app import celery_app
from common.config import get_state
from common.task_broker import TaskBroker

from worker.content import Content
from worker.handler import ModelHandler

logger = logging.getLogger(__name__)

state = get_state()
broker = TaskBroker(state.broker_url, ttl_seconds=state.vizioner_content_ttl)
handler = ModelHandler()
content = Content()

_model_lock = threading.Lock()
_current_model_id: str | None = None

@celery_app.task(name="vizioner.generate_content")
def generate_content(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not broker.task_exists(task_id):
        return {"task_id": task_id, "status": "CANCELLED"}
    model_id = payload.get("model_id", "unknown")
    _maybe_release_gpu(model_id)
    broker.update_task(task_id, status="STARTED", progress=0)

    def _progress_cb(percent: float) -> None:
        if not broker.task_exists(task_id):
            return
        broker.update_task(task_id, status="IN_PROGRESS", progress=min(0.95, float(percent)))

    try:
        files: list[str] = handler.handle(
            model_id=model_id,
            payload=payload,
            tempdir=state.worker_tempdir,
            progress_callback=_progress_cb,
        )
        if not broker.task_exists(task_id):
            _remove_local(files)
            return {"task_id": task_id, "status": "CANCELLED"}
        prefix = f"tasks/{task_id}/{model_id}"
        broker.update_task(task_id, status="IN_PROGRESS", progress=95.0)
        contents: list[str] = content.upload_files(files, prefix=prefix)
        broker.update_task(task_id, status="SUCCESS", progress=100.0, contents=contents)
        _remove_local(files)
        _schedule_auto_purge(task_id)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=state.vizioner_content_ttl)
        return {"task_id": task_id, "expires_at": expires_at.isoformat()}
    except Exception as error:
        logger.exception(str(error))
        broker.update_task(task_id, status="ERROR", progress=0, contents=[])
        return {"task_id": task_id, "expires_at": 0}


@celery_app.task(
    name="vizioner.purge_task",
    bind=True,
    max_retries=5,
    default_retry_delay=5,
)
def purge_task(self, task_id: str) -> dict[str, Any]:
    prefix = Content.task_prefix(task_id)
    try:
        deleted = content.delete_prefix(prefix)
    except Exception as error:
        if _is_retryable_s3_error(error):
            raise self.retry(exc=error, countdown=min(60, 2**self.request.retries))
        raise
    broker.delete_task(task_id)
    return {"task_id": task_id, "deleted": deleted, "prefix": prefix}


def _maybe_release_gpu(model_id: str) -> None:
    global _current_model_id
    with _model_lock:
        if _current_model_id and _current_model_id != model_id:
            _current_model_id = None
        _current_model_id = model_id


def _remove_local(files: list[str]) -> None:
    for file in files:
        if file:
            while os.path.exists(file):
                os.remove(file)


def _schedule_auto_purge(task_id: str) -> None:
    celery_app.send_task("vizioner.purge_task", args=[task_id], countdown=state.vizioner_content_ttl)


def _is_retryable_s3_error(exception: Exception) -> bool:
    if isinstance(exception, ClientError):
        code = str(exception.response.get("Error", {}).get("Code", ""))
        return code in {"SlowDown", "InternalError", "ServiceUnavailable", "RequestTimeout"}
    return False
