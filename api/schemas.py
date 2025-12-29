from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    model_id: str
    type: str
    description: str


class ModelsResponse(BaseModel):
    models: List[ModelInfo]


class CreateTaskRequest(BaseModel):
    input_id: Optional[Any] = Field(default=None)
    model_id: str
    prompt: str
    num_inference_steps: int
    guidance_scale: float


class CreateImageRequest(CreateTaskRequest):
    height: int
    width: int
    num_images_per_prompt: int


class CreateAudioRequest(CreateTaskRequest):
    audio_end_in_s: float
    num_waveforms_per_prompt: int


class CreateVideoRequest(CreateTaskRequest):
    height: int
    width: int
    num_frames: int
    num_videos_per_prompt: int


class CreateTaskResponse(BaseModel):
    task_id: str


class TasksResponse(BaseModel):
    tasks: List[str]


class StatusResponse(BaseModel):
    status: str
    progress: float


class ResultResponse(BaseModel):
    input_id: Optional[Any] = Field(default=None)
    task_id: str
    contents: List[str]


class DeleteTaskRequest(BaseModel):
    task_id: str


class DeleteTaskResponse(BaseModel):
    result: str
