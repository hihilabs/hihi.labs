FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    openssh-client \
    && curl -fsSL https://github.com/docker/compose/releases/download/v2.27.1/docker-compose-linux-x86_64 \
       -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Channel layer is Redis-backed now (REDIS_CHANNEL_URL) — workers can scale,
# but PRESENCE dict in whiteboards/consumers.py is still per-process; keep 1
# worker until that moves to Redis too.
CMD python manage.py migrate --noinput && \
    gunicorn hihilabs.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 1 --timeout 120 --reload --access-logfile -
