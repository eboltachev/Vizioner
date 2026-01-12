import wave
from uuid import uuid4

import numpy as np
from PIL import Image


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
    for _ in range(num_images_per_prompt):
        filename = f"{tempdir}/{uuid4()}.png"
        data = np.random.randint(low=0, high=256, size=(height, width, 3), dtype=np.uint8)
        img = Image.fromarray(data)
        img.save(filename)
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
    for _ in range(num_videos_per_prompt):
        filename = f"{tempdir}/{uuid4()}.jpg"
        data = np.random.randint(low=0, high=256, size=(height, width, 3), dtype=np.uint8)
        img = Image.fromarray(data)
        img.save(filename)
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
    duration_sec = audio_end_in_s
    sample_rate = 44100
    frequency = 440.0
    files = []
    for _ in range(num_waveforms_per_prompt):
        filename = f"{tempdir}/{uuid4()}.wav"
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * frequency * t)
        audio = np.int16(signal * 32767)
        with wave.open(filename, "w") as wf:
            wf.setnchannels(1)  # mono
            wf.setsampwidth(2)  # 16 bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        files.append(filename)
    _log(files)
    return files
