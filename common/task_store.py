from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import redis


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    input_id: Any
    contents: list[str]


class TaskStore:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def register_task(self, task_id: str, payload: dict[str, Any]) -> None:
        created_at = datetime.now(tz=timezone.utc).isoformat()
        task_data = {
            "status": "PENDING",
            "progress": 0,
            "created_at": created_at,
            "model_id": payload.get("model_id"),
            "input_id": payload.get("input_id"),
            "contents": json.dumps([]),
        }
        self._client.hset(self._task_key(task_id), mapping=task_data)
        self._client.rpush("tasks", task_id)

    def update_task(self, task_id: str, **fields: Any) -> None:
        if "contents" in fields:
            fields = {**fields, "contents": json.dumps(fields["contents"])}
        self._client.hset(self._task_key(task_id), mapping=fields)

    def get_task(self, task_id: str) -> dict[str, Any]:
        data = self._client.hgetall(self._task_key(task_id))
        if not data:
            return {}
        if "contents" in data:
            data["contents"] = json.loads(data["contents"]) if data["contents"] else []
        return data

    def list_tasks(self) -> list[str]:
        return [task_id for task_id in self._client.lrange("tasks", 0, -1) if task_id]

    def delete_task(self, task_id: str) -> None:
        self._client.delete(self._task_key(task_id))
        self._client.lrem("tasks", 0, task_id)

    @staticmethod
    def _task_key(task_id: str) -> str:
        return f"task:{task_id}"
