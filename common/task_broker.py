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


class TaskBroker:
    def __init__(self, broker_url: str) -> None:
        self._client = redis.Redis.from_url(broker_url, decode_responses=True)

    def register_task(self, task_id: str, payload: dict[str, Any]) -> None:
        created_at = datetime.now(tz=timezone.utc).isoformat()
        task_data = {
            "status": "PENDING",
            "progress": 0,
            "created_at": created_at,
            "model_id": payload.get("model_id"),
            "input_id": json.dumps(payload.get("input_id"), ensure_ascii=False),
            "contents": json.dumps([]),
        }
        self._client.hset(self._task_key(task_id), mapping=self._sanitize_mapping(task_data))
        self._client.rpush("tasks", task_id)

    def update_task(self, task_id: str, **fields: Any) -> None:
        if "contents" in fields:
            fields = {**fields, "contents": json.dumps(fields["contents"])}
        if "input_id" in fields:
            fields = {**fields, "input_id": json.dumps(fields["input_id"], ensure_ascii=False)}
        self._client.hset(self._task_key(task_id), mapping=self._sanitize_mapping(fields))

    def get_task(self, task_id: str) -> dict[str, Any]:
        data = self._client.hgetall(self._task_key(task_id))
        if not data:
            return {}
        if "contents" in data:
            data["contents"] = json.loads(data["contents"]) if data["contents"] else []
        if "input_id" in data:
            raw = data["input_id"]
            if raw:
                try:
                    data["input_id"] = json.loads(raw)
                except json.JSONDecodeError:
                    data["input_id"] = raw
            else:
                data["input_id"] = None
        return data

    def list_tasks(self) -> list[str]:
        return [task_id for task_id in self._client.lrange("tasks", 0, -1) if task_id]

    def delete_task(self, task_id: str) -> None:
        self._client.delete(self._task_key(task_id))
        self._client.lrem("tasks", 0, task_id)

    @staticmethod
    def _task_key(task_id: str) -> str:
        return f"task:{task_id}"

    @staticmethod
    def _redis_encode(value: Any) -> str | int | float | bytes:
        if value is None:
            return ""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (bytes, str, int, float)):
            return value
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def _sanitize_mapping(cls, mapping: Mapping[str, Any]) -> dict[str, str | int | float | bytes]:
        return {k: cls._redis_encode(v) for k, v in mapping.items()}
