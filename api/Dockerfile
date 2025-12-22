FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ../common /app/common
COPY . /app/api

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/common /app/api

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
