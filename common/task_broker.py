from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import redis


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    input_id: Any
    contents: list[str]


class TaskBroker:
    def __init__(self, broker_url: str, *, ttl_seconds: int) -> None:
        self._client = redis.Redis.from_url(broker_url, decode_responses=True)
        self._ttl_seconds = max(int(ttl_seconds), 1)

    def register_task(self, task_id: str, payload: dict[str, Any]) -> None:
        now = datetime.now(tz=timezone.utc)
        created_at = now.isoformat()
        expires_at = (now + timedelta(seconds=self._ttl_seconds)).isoformat()

        task_data = {
            "status": "PENDING",
            "progress": 0,
            "created_at": created_at,
            "expires_at": expires_at,
            "model_id": payload.get("model_id"),
            "input_id": json.dumps(payload.get("input_id"), ensure_ascii=False),
            "contents": json.dumps([]),
        }

        key = self._task_key(task_id)
        pipe = self._client.pipeline()
        pipe.hset(key, mapping=self._sanitize_mapping(task_data))
        pipe.expire(key, self._ttl_seconds)
        pipe.execute()

    def update_task(self, task_id: str, **fields: Any) -> None:
        key = self._task_key(task_id)
        if not self._client.exists(key):
            return
        if "contents" in fields:
            fields = {**fields, "contents": json.dumps(fields["contents"])}
        if "input_id" in fields:
            fields = {**fields, "input_id": json.dumps(fields["input_id"], ensure_ascii=False)}
        pipe = self._client.pipeline()
        pipe.hset(key, mapping=self._sanitize_mapping(fields))
        pipe.hget(key, "expires_at")
        response = pipe.execute()
        expires_at_raw = response[-1]
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw)
                now = datetime.now(tz=timezone.utc)
                remaining = int((expires_at - now).total_seconds())
                if remaining <= 0:
                    self._client.delete(key)
                else:
                    self._client.expire(key, remaining)
            except Exception:
                self._client.expire(key, self._ttl_seconds)

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

    def task_exists(self, task_id: str) -> bool:
        return bool(self._client.exists(self._task_key(task_id)))

    def list_tasks(self) -> list[str]:
        ids: list[str] = []
        for key in self._client.scan_iter(match="task:*", count=1000):
            ids.append(key.split("task:", 1)[-1])
        ids.sort()
        return ids

    def delete_task(self, task_id: str) -> None:
        self._client.delete(self._task_key(task_id))

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
        return {key: cls._redis_encode(value) for key, value in mapping.items()}
