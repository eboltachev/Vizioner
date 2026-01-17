from __future__ import annotations

import os
import inspect
from pathlib import Path
import time
from collections.abc import Callable
from uuid import uuid4

import soundfile
import torch
from diffusers import DiffusionPipeline, EulerDiscreteScheduler, FluxPipeline, StableAudioPipeline
from diffusers.utils import export_to_video, load_image

torch.cuda.set_per_process_memory_fraction(0.95, device=0)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

ProgressCallback = Callable[[float], None]

def create_images(
    model_path: Path,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    height: int,
    width: int,
    num_images_per_prompt: int,
    tempdir: str,
    progress_callback: ProgressCallback | None = None,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_path, dtype=torch.bfloat16, device_map="cuda")
    progress_kwargs = _build_progress_kwargs(
        pipe, num_inference_steps=num_inference_steps, progress_callback=progress_callback
    )
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        height=height,
        width=width,
        num_images_per_prompt=num_images_per_prompt,
        **progress_kwargs,
    )
    for image in response.images:
        filename = f"{tempdir}/{uuid4()}.png"
        image.save(filename)
        files.append(filename)
    _log(files)
    return files


def create_audios(
    model_path: Path,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    audio_end_in_s: float,
    num_waveforms_per_prompt: int,
    tempdir: str,
    progress_callback: ProgressCallback | None = None,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_path, dtype=torch.float16, device_map="cuda")
    progress_kwargs = _build_progress_kwargs(
        pipe, num_inference_steps=num_inference_steps, progress_callback=progress_callback
    )
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        audio_end_in_s=audio_end_in_s,
        num_waveforms_per_prompt=num_waveforms_per_prompt,
        **progress_kwargs,
    )
    for audio in response.audios:
        filename = f"{tempdir}/{uuid4()}.wav"
        output = audio.T.float().cpu().numpy()
        soundfile.write(filename, output, pipe.vae.sampling_rate)
        files.append(filename)
    _log(files)
    return files


def create_videos(
    model_path: Path,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    height: int,
    width: int,
    num_frames: int,
    num_videos_per_prompt: int,
    tempdir: str,
    progress_callback: ProgressCallback | None = None,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_path, dtype=torch.bfloat16, device_map="cuda")
    progress_kwargs = _build_progress_kwargs(
        pipe, num_inference_steps=num_inference_steps, progress_callback=progress_callback
    )
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        height=height,
        width=width,
        num_frames=num_frames,
        num_videos_per_prompt=num_videos_per_prompt,
        **progress_kwargs,
    )
    for video in response.frames:
        filename = f"{tempdir}/{uuid4()}.mp4"
        export_to_video(video, filename, fps=16)
        files.append(filename)
    _log(files)
    return files

def _build_progress_kwargs(
    pipe: DiffusionPipeline,
    *,
    num_inference_steps: int,
    progress_callback: ProgressCallback | None,
    min_delta_percent: float = 1.0,
    min_interval_s: float = 0.5,
) -> dict:
    if not progress_callback or not num_inference_steps or num_inference_steps <= 0:
        return {}

    sig = inspect.signature(pipe.__call__)
    params = sig.parameters

    last_emit_percent = -1.0
    last_emit_ts = 0.0

    def _emit(step: int) -> None:
        nonlocal last_emit_percent, last_emit_ts
        pct = (float(step + 1) / float(num_inference_steps)) * 100.0
        if pct > 100.0:
            pct = 100.0
        now = time.monotonic()
        if (pct - last_emit_percent) >= min_delta_percent or (now - last_emit_ts) >= min_interval_s or pct >= 100.0:
            last_emit_percent = pct
            last_emit_ts = now
            progress_callback(pct)

    if "callback_on_step_end" in params:

        def _on_step_end(pipeline, step: int, timestep: int, callback_kwargs: dict):
            _emit(step)
            return callback_kwargs

        kwargs: dict = {"callback_on_step_end": _on_step_end}
        if "callback_on_step_end_tensor_inputs" in params:
            kwargs["callback_on_step_end_tensor_inputs"] = []
        return kwargs
    if "callback" in params:

        def _callback(step: int, timestep: int, latents=None):
            _emit(step)

        kwargs = {"callback": _callback}
        if "callback_steps" in params:
            kwargs["callback_steps"] = 1
        return kwargs
    return {}


def _log(value: object) -> None:
    print(f"{value=}")


