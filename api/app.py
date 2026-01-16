from __future__ import annotations

import uuid
from pathlib import Path
import logging

from common.celery_app import celery_app
from common.config import get_state
from common.models_catalog import load_models
from common.task_broker import TaskBroker
from fastapi import FastAPI, HTTPException

from schemas import (
    CreateAudioRequest,
    CreateImageRequest,
    CreateTaskResponse,
    CreateVideoRequest,
    DeleteTaskRequest,
    DeleteTaskResponse,
    ModelInfo,
    ModelsResponse,
    ResultResponse,
    StatusResponse,
    TasksResponse,
)

logger = logging.getLogger(__name__)
state = get_state()
broker = TaskBroker(state.broker_url, ttl_seconds=state.vizioner_content_ttl)
models_root = Path("/models")

app = FastAPI(title="Vizioner")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models", response_model=ModelsResponse, status_code=200)
async def models() -> ModelsResponse:
    models = [
        ModelInfo(model_id=model.id, type=model.type, description=model.description)
        for model in load_models(models_root)
    ]
    logger.info(f"{models=}")
    return ModelsResponse(models=models)


@app.post("/create_image", response_model=CreateTaskResponse, status_code=201)
async def create_image(request: CreateImageRequest) -> CreateTaskResponse:
    available_models = {model.id for model in load_models(models_root)}
    if request.model_id not in available_models:
        raise HTTPException(status_code=400, detail="Unknown model")
    task_id = str(uuid.uuid4())
    payload = request.model_dump()
    broker.register_task(task_id, payload)
    celery_app.send_task("vizioner.purge_task", args=[task_id], countdown=state.vizioner_content_ttl)
    celery_app.send_task("vizioner.generate_content", args=[task_id, payload])
    logger.info(f"Registred image task, {task_id=}, {payload=}")
    return CreateTaskResponse(task_id=task_id)


@app.post("/create_audio", response_model=CreateTaskResponse, status_code=201)
async def create_audio(request: CreateAudioRequest) -> CreateTaskResponse:
    available_models = {model.id for model in load_models(models_root)}
    if request.model_id not in available_models:
        raise HTTPException(status_code=400, detail="Unknown model")
    task_id = str(uuid.uuid4())
    payload = request.model_dump()
    broker.register_task(task_id, payload)
    celery_app.send_task("vizioner.purge_task", args=[task_id], countdown=state.vizioner_content_ttl)
    celery_app.send_task("vizioner.generate_content", args=[task_id, payload])
    logger.info(f"Registred audio task, {task_i=}, {payloa=}")
    return CreateTaskResponse(task_id=task_id)


@app.post("/create_video", response_model=CreateTaskResponse, status_code=201)
async def create_video(request: CreateVideoRequest) -> CreateTaskResponse:
    available_models = {model.id for model in load_models(models_root)}
    if request.model_id not in available_models:
        raise HTTPException(status_code=400, detail="Unknown model")
    task_id = str(uuid.uuid4())
    payload = request.model_dump()
    broker.register_task(task_id, payload)
    celery_app.send_task("vizioner.purge_task", args=[task_id], countdown=state.vizioner_content_ttl)
    celery_app.send_task("vizioner.generate_content", args=[task_id, payload])
    logger.info(f"Registred video task, {task_id=}, {payload=}")
    return CreateTaskResponse(task_id=task_id)


@app.get("/tasks", response_model=TasksResponse, status_code=200)
async def tasks() -> TasksResponse:
    tasks = broker.list_tasks()
    logger.info(f"{tasks=}")
    return TasksResponse(tasks=tasks)


@app.get("/status", response_model=StatusResponse, status_code=200)
async def get_status(task_id: str) -> StatusResponse:
    task = broker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"{task=}")
    return StatusResponse(status=task.get("status", "PENDING"), progress=task.get("progress", 0.0))


@app.get("/result", response_model=ResultResponse, status_code=200)
async def result(task_id: str) -> ResultResponse:
    task = broker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"{task=}")
    return ResultResponse(input_id=task.get("input_id"), task_id=task_id, contents=task.get("contents", []))


@app.delete("/delete", response_model=DeleteTaskResponse, status_code=200)
async def delete(request: DeleteTaskRequest) -> DeleteTaskResponse:
    task = broker.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    broker.delete_task(request.task_id)
    celery_app.send_task("vizioner.purge_task", args=[request.task_id], countdown=0)
    logger.info(f"Delete {task_id=}")
    return DeleteTaskResponse(result="SUCCESS")
