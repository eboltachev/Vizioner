from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.celery_app import celery_app
from common.config import get_state
from common.models_catalog import load_models
from common.task_store import TaskStore

settings = get_state()
store = TaskStore(settings.redis_url)
models_root = Path("/models")

app = FastAPI(title="Vizioner")


class CreateRequest(BaseModel):
    input_id: Optional[Any] = Field(default=None)
    model_id: str
    prompt: str

    model_config = {"extra": "allow"}


class DeleteRequest(BaseModel):
    task_id: str


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
async def models() -> dict[str, list[dict[str, str]]]:
    models_info = load_models(models_root)
    return {
        "models": [
            {
                "id": model.id,
                "type": model.type,
                "descriprtion": model.description,
            }
            for model in models_info
        ]
    }


@app.post("/create", status_code=201)
async def create(request: CreateRequest) -> dict[str, str]:
    available_models = {model.id for model in load_models(models_root)}
    if request.model_id not in available_models:
        raise HTTPException(status_code=400, detail="Unknown model")
    task_id = str(uuid.uuid4())
    payload = request.model_dump()
    store.register_task(task_id, payload)
    celery_app.send_task("vizioner.generate_content", args=[task_id, payload])
    return {"id": task_id}


@app.get("/tasks")
async def tasks() -> dict[str, list[str]]:
    return {"tasks": store.list_tasks()}


@app.get("/status")
async def status(task_id: str) -> dict[str, Any]:
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "status": task.get("status", "PENDING"),
        "progress": int(task.get("progress", 0)),
    }


@app.get("/result")
async def result(task_id: str) -> dict[str, list[dict[str, Any]]]:
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "results": [
            {
                "input_id": task.get("input_id"),
                "task_id": task_id,
                "contents": task.get("contents", []),
            }
        ]
    }


@app.delete("/delete")
async def delete(request: DeleteRequest) -> dict[str, str]:
    store.delete_task(request.task_id)
    return {"result": "SUCCESS"}
