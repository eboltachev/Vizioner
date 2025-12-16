from typing import Dict

import pytest
import requests
from dotenv import load_dotenv
from e2e.test_core import TestCore

load_dotenv()


@pytest.mark.asyncio
class TestHealth(TestCore):
    async def test_docs(self):
        response = requests.get(f"{self._api_url}/docs")
        assert 200 == response.status_code
        assert "FastAPI - Swagger UI" in response.text

    async def test_health(self):
        response = requests.get(f"{self._api_url}/health")
        assert 200 == response.status_code
        assert {"status": "ok"} == response.json()
