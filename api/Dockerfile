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
COPY ./api/app.py ./
COPY ./api/.python-version ./
COPY ./common ./common
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENTRYPOINT uv run uvicorn app:app --host ${API_HOST} --port ${API_PORT}
