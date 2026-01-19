from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, List

from worker.executors.image import create_images
from worker.executors.audio import create_audios
from worker.executors.video import create_videos

ProgressCallback = Callable[[float], None]


class ModelHandler:
    def handle(self, payload: dict[str, Any]) -> List[str]:
        handler = self._get_handler(model_type=payload.get("model_type", "unknown"))
        return handler(payload=payload)

    def _get_handler(self, model_type: str) -> Callable:
        match model_type:
            case "text_to_image":
                return self._handle_text_to_image
            case "text_to_audio":
                return self._handle_text_to_audio
            case "text_to_video":
                return self._handle_text_to_video

    def _handle_text_to_image(self, payload: dict[str, Any]) -> List[str]:
        return create_images(
            model_path=payload.get("model_path", "unknown"),
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            height=payload.get("height", 128) or 128,
            width=payload.get("width", 128) or 128,
            num_images_per_prompt=payload.get("num_images_per_prompt", 1) or 1,
            tempdir=payload.get("tempdir", "/tmp"),
            progress_callback=payload.get("progress_callback"),
        )

    def _handle_text_to_video(self, payload: dict[str, Any]) -> List[str]:
        return create_videos(
            model_path=payload.get("model_path", "unknown"),
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            height=payload.get("height", 128) or 128,
            width=payload.get("width", 128) or 128,
            num_frames=payload.get("num_frames", 80) or 80,
            num_videos_per_prompt=payload.get("num_videos_per_prompt", 1) or 1,
            tempdir=payload.get("tempdir", "/tmp"),
            progress_callback=payload.get("progress_callback"),
        )

    def _handle_text_to_audio(self, payload: dict[str, Any]) -> List[str]:
        return create_audios(
            model_path=payload.get("model_path", "unknown"),
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            audio_end_in_s=payload.get("audio_end_in_s", 5.0) or 5.0,
            num_waveforms_per_prompt=payload.get("num_waveforms_per_prompt", 1) or 1,
            tempdir=payload.get("tempdir", "/tmp"),
            progress_callback=payload.get("progress_callback"),
        )
