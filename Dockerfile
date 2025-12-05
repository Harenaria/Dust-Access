FROM python:3.11-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install "poetry==1.8.2"
RUN poetry config virtualenvs.create false
WORKDIR /app
COPY pyproject.toml ./
RUN poetry lock && poetry install --no-interaction --no-ansi --no-root

# Copia tutto il resto del codice
COPY . .

# Espone la porta
EXPOSE 8080