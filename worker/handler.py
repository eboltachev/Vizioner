from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, List

from worker.generator import create_audios, create_images, create_videos

ProgressCallback = Callable[[float], None]


class ModelHandler:
    def __init__(self, model_id: str, model_type: str, models_root: Path):
        self.model_id = model_id
        self.model_type = model_type
        self.models_root = models_root
        self.handler = self._get_handler(model_type)


    def handle(
        self, payload: dict[str, Any], tempdir: str, progress_callback: ProgressCallback | None = None
    ) -> List[str]:
        model_path = self.models_root / self.model_type / self.model_id
        return self.handler(model_path=model_path, payload=payload, tempdir=tempdir, progress_callback=progress_callback)

    def _get_handler(self, model_type: str) -> Callable:
        match model_type:
            case "text_to_image":
                return self._handle_text_to_image
            case "text_to_audio":
                return self._handle_text_to_audio
            case "text_to_video":
                return self._handle_text_to_video

    def _handle_text_to_image(
        self,
        model_path: Path,
        payload: dict[str, Any],
        tempdir: str,
        progress_callback: ProgressCallback | None = None,
    ) -> List[str]:
        return create_images(
            model_path=model_path,
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            height=payload.get("height", 128) or 128,
            width=payload.get("width", 128) or 128,
            num_images_per_prompt=payload.get("num_images_per_prompt", 1) or 1,
            tempdir=tempdir,
            progress_callback=progress_callback,
        )

    def _handle_text_to_video(
        self,
        model_path: Path,
        payload: dict[str, Any],
        tempdir: str,
        progress_callback: ProgressCallback | None = None,
    ) -> List[str]:
        return create_videos(
            model_path=model_path,
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            height=payload.get("height", 128) or 128,
            width=payload.get("width", 128) or 128,
            num_frames=payload.get("num_frames", 80) or 80,
            num_videos_per_prompt=payload.get("num_videos_per_prompt", 1) or 1,
            tempdir=tempdir,
            progress_callback=progress_callback,
        )

    def _handle_text_to_audio(
        self,
        model_path: Path,
        payload: dict[str, Any],
        tempdir: str,
        progress_callback: ProgressCallback | None = None,
    ) -> List[str]:
        return create_audios(
            model_path=model_path,
            prompt=payload.get("prompt", ""),
            num_inference_steps=payload.get("num_inference_steps", 10) or 10,
            guidance_scale=payload.get("guidance_scale", 3.5) or 3.5,
            audio_end_in_s=payload.get("audio_end_in_s", 5.0) or 5.0,
            num_waveforms_per_prompt=payload.get("num_waveforms_per_prompt", 1) or 1,
            tempdir=tempdir,
            progress_callback=progress_callback,
        )
