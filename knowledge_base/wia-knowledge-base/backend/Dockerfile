FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=5
WORKDIR /srv

COPY requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r /srv/backend/requirements.txt

COPY . /srv/backend

# Run from /srv so imports are always `backend.*` (keeps backend/logging from shadowing stdlib)
# Railway routes to $PORT; locally (docker compose) it is unset and the API listens on 8000.
CMD ["sh", "-c", "exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
