FROM python:3.12-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
COPY .agents/ ./.agents/
COPY tests/ ./tests/

RUN pip install ".[test]" \
    && pytest

# --- Production stage ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
COPY .agents/ ./.agents/

# Install dependencies and Playwright browser
RUN pip install . \
    && python -m playwright install --with-deps chromium \
    && rm -rf /root/.cache/pip

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

ENTRYPOINT ["python", "-m", "main"]
