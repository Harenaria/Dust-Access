FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install poetry
RUN poetry config virtualenvs.create false
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --no-dev
COPY . .
EXPOSE 8080