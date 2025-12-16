import os
import re
import subprocess
from time import sleep

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.asyncio
class TestCore:
    def setup_class(self):
        self._sleep = 1
        self._timeout = 100
        self._compose_file = "docker-compose.yml"
        content_cmd = [
            "printdirtree",
            "--exclude-dir",
            "tests",
            "dev",
            "models",
            ".env",
            ".venv",
            "uv.lock",
            ".pytest_cache",
            ".mypy_cache",
            ".flake8",
            "README.md",
            "--show-contents",
        ]
        self.content_file_path = "dev/content.txt"
        self.logs_file_path = "dev/logs.txt"
        os.makedirs("dev", exist_ok=True)
        self._cwd = os.getcwd()
        with open(self.content_file_path, "w") as content_file:
            subprocess.run(content_cmd, cwd=self._cwd, stdout=content_file, stderr=content_file)
        with open(self.logs_file_path, "w") as logs_file:
            logs_file.write("**Logs**\n\n")
        with open(self.logs_file_path, "a") as logs_file:
            subprocess.run(
                ["docker", "compose", "-f", self._compose_file, "up", "--build", "-d", "generative-ai"],
                stdout=logs_file,
                stderr=logs_file,
            )

        self._api_host = os.environ.get("GENERATIVE_API_HOST", "localhost")
        self._api_port = os.environ.get("GENERATIVE_API_PORT", 8000)
        self._api_url = f"http://{self._api_host}:{self._api_port}"
        self._headers = {}
        self._id_pattern = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"

        connection = False
        timeout_counter = 0
        while not connection:
            try:
                requests.get(self._api_url)
                connection = True
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
                sleep(self._sleep)
                timeout_counter += 1
                if timeout_counter > self._timeout:
                    raise Exception("Setup timeout")

    def teardown_class(self):
        with open(self.logs_file_path, "a") as logs_file:
            logs_file.write(f"\n\n**Logs:**\n\n")
        with open(self.logs_file_path, "a") as logs_file:
            subprocess.run(
                ["docker", "compose", "-f", self._compose_file, "logs", "generative-ai"],
                cwd=self._cwd,
                stdout=logs_file,
                stderr=logs_file,
            )
        subprocess.run(
            ["docker", "compose", "-f", self._compose_file, "down", "generative-ai"],
            cwd=self._cwd,
            stdout=open(os.devnull, "w"),
            stderr=subprocess.STDOUT,
        )
