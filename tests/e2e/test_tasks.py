import re
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

    async def test_create_one(self):
        payload = dict(
            input_id=123,
            prompt="Astronaut in a jungle, cold color palette, muted colors, detailed, 8k",
            height=128,
            width=128,
            num_images_per_prompt=1,
            num_inference_steps=5,
            guidance_scale=3.5,
        )
        response = requests.post(f"{self._api_url}/image/create", json=payload)
        assert 201 == response.status_code
        data = response.json()
        assert "id" in data
        task_id = data.get("id")
        assert isinstance(task_id, str)
        assert re.match(self._id_pattern, task_id)
        self._tasks.append(task_id)

    async def test_tasks(self):
        response = requests.get(f"{self._api_url}/tasks")
        assert 200 == response.status_code
        data = response.json()
        assert "tasks" in data
        tasks = data.get("tasks")
        assert isinstance(tasks, list)
        assert len(self._tasks) == len(tasks)
        for self_task_id, data_task_id in zip(self._tasks, tasks):
            assert isinstance(self_task_id, str)
            assert isinstance(data_task_id, str)
            assert self_task_id == data_task_id
