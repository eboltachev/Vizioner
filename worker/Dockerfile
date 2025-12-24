FROM python:3.12

WORKDIR /app
COPY ./api/pyproject.toml ./
COPY ./api/uv.lock ./


RUN apt update && \                                                                                        
    apt install -y curl vim && \                                                                           
    pip install --upgrade pip && \                                                                         
    pip install uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY ./worker/tasks.py ./
COPY ./worker/handler.py ./
COPY ./api/.python-version ./
COPY ./common ./common

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENTRYPOINT uv run celery -A common.celery_app worker --loglevel=info --concurrency=${VIZIONER_WORKER_NUMBER:-1}
