FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/src /app/backend/src
COPY scripts /app/scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "debug_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
