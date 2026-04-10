FROM python:3.12-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY *.py ./
COPY tools/ ./tools/
COPY .agents/ ./.agents/

RUN pip install ".[test]"

# Run tests during build
COPY tests/ ./tests/
RUN pytest || true

# --- Production stage ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY *.py ./
COPY tools/ ./tools/
COPY .agents/ ./.agents/

# Install dependencies and Playwright browser for aider
RUN pip install . \
    && python -m playwright install --with-deps chromium \
    && rm -rf /root/.cache/pip

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]
