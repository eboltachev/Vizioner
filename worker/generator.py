from uuid import uuid4

import soundfile
import torch
from diffusers import DiffusionPipeline, EulerDiscreteScheduler, StableAudioPipeline, FluxPipeline
from diffusers.utils import export_to_video, load_image

import torch
import os

torch.cuda.set_per_process_memory_fraction(0.95, device=0)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

def _log(value: object) -> None:
    print(f"{value=}")


def create_images(
    model_id: str,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    height: int,
    width: int,
    num_images_per_prompt: int,
    tempdir: str,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda")
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        height=height,
        width=width,
        num_images_per_prompt=num_images_per_prompt,
    )
    for image in response.images:
        filename = f"{tempdir}/{uuid4()}.png"
        image.save(filename)
        files.append(filename)
    _log(files)
    return files


def create_audios(
    model_id: str,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    audio_end_in_s: float,
    num_waveforms_per_prompt: int,
    tempdir: str,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_id, dtype=torch.float16, device_map="cuda")
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        audio_end_in_s=audio_end_in_s,
        num_waveforms_per_prompt=num_waveforms_per_prompt,
    )
    for audio in response.audios:
        filename = f"{tempdir}/{uuid4()}.wav"
        output = audio.T.float().cpu().numpy()
        soundfile.write(filename, output, pipe.vae.sampling_rate)
        files.append(filename)
    _log(files)
    return files


def create_videos(
    model_id: str,
    prompt: str,
    num_inference_steps: int,
    guidance_scale: float,
    height: int,
    width: int,
    num_frames: int,
    num_videos_per_prompt: int,
    tempdir: str,
) -> list:
    files = []
    pipe = DiffusionPipeline.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda")
    response = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        height=height,
        width=width,
        num_frames=num_frames,
        num_videos_per_prompt=num_videos_per_prompt,
    )
    for video in response.frames:
        filename = f"{tempdir}/{uuid4()}.mp4"
        export_to_video(video, filename, fps=16)
        files.append(filename)
    _log(files)
    return files
