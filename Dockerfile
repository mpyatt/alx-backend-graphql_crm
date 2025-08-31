# Dockerfile
FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  VIRTUAL_ENV=/opt/venv \
  PATH="/opt/venv/bin:$PATH"

# System deps (cron is optional but included for the cron service)
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  cron \
  && rm -rf /var/lib/apt/lists/*

# Create isolated venv and upgrade pip early (better caching)
RUN python -m venv "$VIRTUAL_ENV" && pip install --upgrade pip

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint separately to set permissions before switching user
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy the rest of the project
COPY . /app

# Create a non-root user and take ownership
RUN useradd -m -u 1000 app \
  && chown -R app:app /app \
  && mkdir -p /app/tmp && chown -R app:app /app/tmp

USER app

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
