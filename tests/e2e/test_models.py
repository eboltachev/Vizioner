from typing import Dict

import pytest
import requests
from dotenv import load_dotenv
from e2e.test_core import TestCore

load_dotenv()


@pytest.mark.asyncio
class TestModels(TestCore):
    async def test_get_model_list(self):
        response = requests.get(f"{self._api_url}/models")
        assert 200 == response.status_code
        data = response.json()
        assert "models" in data
        models = data.get("models")
        assert isinstance(models, list)
        assert models
        for model in models:
            model_id = model.get("id")
            model_type = model.get("type")
            model_descriprtion = model.get("descriprtion")
            assert isinstance(model_id, str)
            assert isinstance(model_type, str)
            assert isinstance(model_descriprtion, str)

    async def test_health(self):
        response = requests.get(f"{self._api_url}/health")
        assert 200 == response.status_code
        assert {"status": "ok"} == response.json()
