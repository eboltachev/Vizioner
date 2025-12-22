from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from common.celery_app import celery_app
from common.config import get_state
from common.task_store import TaskStore
from worker.handler import ModelHandler

settings = get_state()
store = TaskStore(settings.redis_url)
handler = ModelHandler()
_model_lock = threading.Lock()
_current_model_id: str | None = None


def _maybe_release_gpu(model_id: str) -> None:
    global _current_model_id
    with _model_lock:
        if _current_model_id and _current_model_id != model_id:
            _current_model_id = None
        _current_model_id = model_id


def _determine_output_count(payload: dict[str, Any]) -> int:
    if "num_images_per_prompt" in payload:
        return int(payload.get("num_images_per_prompt") or 1)
    if "num_videos_per_prompt" in payload:
        return int(payload.get("num_videos_per_prompt") or 1)
    if "num_waveforms_per_prompt" in payload:
        return int(payload.get("num_waveforms_per_prompt") or 1)
    return 1


@celery_app.task(name="vizioner.generate_content")
def generate_content(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    model_id = payload.get("model_id", "unknown")
    _maybe_release_gpu(model_id)
    store.update_task(task_id, status="PENDING", progress=0)
    output_count = _determine_output_count(payload)
    contents: list[str] = []
    for index in range(output_count):
        content_payload = {**payload, "task_id": task_id}
        contents.append(handler.handle(model_id, content_payload, index, output_count))
        store.update_task(task_id, progress=int(((index + 1) / output_count) * 100))
    store.update_task(task_id, status="SUCCESS", progress=100, contents=contents)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=settings.content_ttl)
    return {"task_id": task_id, "expires_at": expires_at.isoformat()}
