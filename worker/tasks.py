from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from common.celery_app import celery_app
from common.config import get_state
from common.task_broker import TaskBroker

from worker.handler import ModelHandler

state = get_state()
broker = TaskBroker(state.broker_url)
handler = ModelHandler()
_model_lock = threading.Lock()
_current_model_id: str | None = None


def _maybe_release_gpu(model_id: str) -> None:
    global _current_model_id
    with _model_lock:
        if _current_model_id and _current_model_id != model_id:
            _current_model_id = None
        _current_model_id = model_id


@celery_app.task(name="vizioner.generate_content")
def generate_content(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    model_id = payload.get("model_id", "unknown")
    _maybe_release_gpu(model_id)
    broker.update_task(task_id, status="PENDING", progress=0)
    try:
        contents: list[str] = handler.handle(model_id=model_id, payload=payload, tempdir=state.worker_tempdir)
        broker.update_task(task_id, status="SUCCESS", progress=100, contents=contents)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=state.vizioner_content_ttl)
        return {"task_id": task_id, "expires_at": expires_at.isoformat()}
    except Exception as error:
        print(f"{error=}")
        broker.update_task(task_id, status="ERROR", progress=100, contents=[])
        return {"task_id": task_id, "error": str(error)}
