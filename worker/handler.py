from __future__ import annotations

import os
from time import sleep
from typing import Any, Callable, List

from worker.content import Content
from worker.mocks import create_audios, create_images, create_videos


class ModelHandler:
    _instance: "ModelHandler | None" = None

    def __new__(cls) -> "ModelHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {
                "FLUX.1-dev": cls._instance._handle_text_to_image,
                "FLUX.2-dev": cls._instance._handle_text_to_image,
                "Wan2.1-T2V-1.3B-Diffusers": cls._instance._handle_text_to_video,
                "Wan2.2-TI2V-5B-Diffusers": cls._instance._handle_text_to_video,
                "stable-audio-open-1.0": cls._instance._handle_text_to_audio,
            }
        return cls._instance

    def handle(
        self,
        model_id: str,
        payload: dict[str, Any],
        tempdir: str,
    ) -> List[str]:
        handler = self._handlers.get(model_id, self._handle_text_to_image)
        return handler(model_id=model_id, payload=payload, tempdir=tempdir)

    def _handle_text_to_image(self, model_id: str, payload: dict[str, Any], tempdir: str) -> List[str]:
        prompt = payload.get("prompt", "")
        num_inference_steps = payload.get("num_inference_steps", 10) or 10
        guidance_scale = payload.get("guidance_scale", 3.5) or 3.5
        height = payload.get("height", 128) or 128
        width = payload.get("width", 128) or 128
        num_images_per_prompt = payload.get("num_images_per_prompt", 1) or 1
        files = create_images(
            model_id=model_id,
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
            num_images_per_prompt=num_images_per_prompt,
            tempdir=tempdir,
        )
        contents = files  # to-do list of s3 paths from variable files
        self._remove(files)
        return contents

    def _handle_text_to_video(self, model_id: str, payload: dict[str, Any], tempdir: str) -> List[str]:
        prompt = payload.get("prompt", "")
        num_inference_steps = payload.get("num_inference_steps", 10) or 10
        guidance_scale = payload.get("guidance_scale", 3.5) or 3.5
        height = payload.get("height", 128) or 128
        width = payload.get("width", 128) or 128
        num_frames = payload.get("num_frames", 80) or 80
        num_videos_per_prompt = payload.get("num_videos_per_prompt", 1) or 1
        files = create_videos(
            model_id=model_id,
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
            num_frames=num_frames,
            num_videos_per_prompt=num_videos_per_prompt,
            tempdir=tempdir,
        )
        contents = files  # to-do list of s3 paths from variable files
        self._remove(files)
        return contents

    def _handle_text_to_audio(self, model_id: str, payload: dict[str, Any], tempdir: str) -> List[str]:
        prompt = payload.get("prompt", "")
        num_inference_steps = payload.get("num_inference_steps", 10) or 10
        guidance_scale = payload.get("guidance_scale", 3.5) or 3.5
        audio_end_in_s = payload.get("audio_end_in_s", 5.0) or 5.0
        num_waveforms_per_prompt = payload.get("num_videos_per_prompt", 1) or 1
        files = create_audios(
            model_id=model_id,
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            audio_end_in_s=audio_end_in_s,
            num_waveforms_per_prompt=num_waveforms_per_prompt,
            tempdir=tempdir,
        )
        contents = files  # to-do list of s3 paths from variable files
        self._remove(files)
        return contents

    def _remove(self, files: List[str]) -> None:
        for file in files:
            if os.path.exists(file):
                os.remove(file)
