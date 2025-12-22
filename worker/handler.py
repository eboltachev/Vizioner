from __future__ import annotations

from typing import Any, Callable


class ModelHandler:
    _instance: "ModelHandler | None" = None

    def __new__(cls) -> "ModelHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {
                "FLUX.1-dev": cls._instance._handle_text_to_image,
                "FLUX.2-dev": cls._instance._handle_text_to_image,
                "Wan2.1-T2V-1.3B-Diffusers": cls._instance._handle_text_to_video,
                "stable-audio-open-1.0": cls._instance._handle_text_to_audio,
            }
        return cls._instance

    def handle(self, model_id: str, payload: dict[str, Any], index: int, total: int) -> str:
        handler = self._handlers.get(model_id, self._handle_default)
        return handler(model_id, payload, index, total)

    def _handle_text_to_image(self, model_id: str, payload: dict[str, Any], index: int, total: int) -> str:
        return f"s3://content/{payload.get('task_id', 'task')}/image/{index}"

    def _handle_text_to_video(self, model_id: str, payload: dict[str, Any], index: int, total: int) -> str:
        return f"s3://content/{payload.get('task_id', 'task')}/video/{index}"

    def _handle_text_to_audio(self, model_id: str, payload: dict[str, Any], index: int, total: int) -> str:
        return f"s3://content/{payload.get('task_id', 'task')}/audio/{index}"

    def _handle_default(self, model_id: str, payload: dict[str, Any], index: int, total: int) -> str:
        return f"s3://content/{payload.get('task_id', 'task')}/{index}"
