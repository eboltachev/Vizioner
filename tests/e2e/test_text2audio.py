import re
from random import choice
from time import sleep
from typing import Dict

import pytest
import requests
from dotenv import load_dotenv
from e2e.test_core import TestCore

load_dotenv()


@pytest.mark.asyncio
class TestImage(TestCore):
    _tasks = []

    async def test_create_one_with_input_id(self):
        payload = dict(
            input_id=123,
            model_id="stable-audio-open-1.0",
            prompt="The sound of a hammer hitting a wooden surface.",
            num_inference_steps=10,
            guidance_scale=4.0,
            audio_end_in_s=8.0,
            num_waveforms_per_prompt=1,
        )
        response = requests.post(f"{self._api_url}/create_audio", json=payload)
        assert 201 == response.status_code
        data = response.json()
        assert "task_id" in data
        task_id = data.get("task_id")
        assert isinstance(task_id, str)
        assert re.match(self._id_pattern, task_id)
        self._tasks.append(task_id)

    async def test_create_one_none_input_id(self):
        payload = dict(
            input_id=None,
            model_id="stable-audio-open-1.0",
            prompt="The sound of a hammer hitting a wooden surface.",
            audio_end_in_s=8.0,
            num_waveforms_per_prompt=1,
            num_inference_steps=10,
            guidance_scale=4.0,
        )
        response = requests.post(f"{self._api_url}/create_audio", json=payload)
        assert 201 == response.status_code
        data = response.json()
        assert "task_id" in data
        task_id = data.get("task_id")
        assert isinstance(task_id, str)
        assert re.match(self._id_pattern, task_id)
        self._tasks.append(task_id)

    async def test_create_one_misstake_input_id(self):
        payload = dict(
            model_id="stable-audio-open-1.0",
            prompt="The sound of a hammer hitting a wooden surface.",
            audio_end_in_s=8.0,
            num_waveforms_per_prompt=1,
            num_inference_steps=10,
            guidance_scale=4.0,
        )
        response = requests.post(f"{self._api_url}/create_audio", json=payload)
        assert 201 == response.status_code
        data = response.json()
        assert "task_id" in data
        task_id = data.get("task_id")
        assert isinstance(task_id, str)
        assert re.match(self._id_pattern, task_id)
        self._tasks.append(task_id)

    async def test_create_several(self):
        payload = dict(
            input_id="0",
            model_id="stable-audio-open-1.0",
            prompt="The sound of a hammer hitting a wooden surface.",
            audio_end_in_s=8.0,
            num_waveforms_per_prompt=3,
            num_inference_steps=10,
            guidance_scale=4.0,
        )
        response = requests.post(f"{self._api_url}/create_audio", json=payload)
        assert 201 == response.status_code
        data = response.json()
        assert "task_id" in data
        task_id = data.get("task_id")
        assert isinstance(task_id, str)
        assert re.match(self._id_pattern, task_id)
        self._tasks.append(task_id)

    async def test_status(self):
        task_id = self._tasks[0]
        params = {"task_id": task_id}
        response = requests.get(f"{self._api_url}/status", params=params)
        assert 200 == response.status_code
        data = response.json()
        assert "status" in data
        status = data.get("status")
        assert isinstance(status, str)
        assert status in {"PENDING", "SUCCESS", "ERROR"}
        timeout_counter = 0
        while status != "SUCCESS":
            response = requests.get(f"{self._api_url}/status", params=params)
            data = response.json()
            status = data.get("status")
            sleep(self._sleep)
            timeout_counter += 1
            if timeout_counter > self._timeout:
                break
        assert status == "SUCCESS"

    async def test_result(self):
        task_id = self._tasks[0]
        params = {"task_id": task_id}
        response = requests.get(f"{self._api_url}/result", params=params)
        assert 200 == response.status_code
        data = response.json()
        assert "contents" in data
        contents = data.get("contents")
        assert isinstance(contents, list)
        assert len(contents) > 0
        assert all([isinstance(content, str) for content in contents])
        assert "input_id" in data
        input_id = data.get("input_id", "-100")
        assert input_id != "-100"
        assert "task_id" in data
        task_id = data.get("task_id")
        assert re.match(self._id_pattern, task_id)

    async def test_delete(self):
        response = requests.get(f"{self._api_url}/tasks")
        data = response.json()
        start_tasks = data.get("tasks")
        assert set(self._tasks) == set(start_tasks)
        task_id = choice(start_tasks)
        payload = {"task_id": task_id}
        response = requests.delete(f"{self._api_url}/delete", json=payload)
        assert 200 == response.status_code
        data = response.json()
        assert "result" in data
        result = data.get("result")
        assert result == "SUCCESS"
