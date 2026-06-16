FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock README.md ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

COPY src/ /app/src/
COPY database/ /app/database/

CMD ["sh", "-c", "cd /app/database && alembic upgrade head && cd /app/src && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
