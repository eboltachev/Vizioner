FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIZIONER_CELERY_IMPORTS=worker.tasks

COPY ../common /app/common
COPY . /app/worker

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/common /app/worker

CMD ["sh", "-c", "celery -A common.celery_app worker --loglevel=info --concurrency=${VIZIONER_WORKER_NUMBER:-1}"]
