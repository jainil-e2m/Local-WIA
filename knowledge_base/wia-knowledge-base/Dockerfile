# Production image for every Railway service: web (API + the built portfolio), worker-bulk and worker-sync.
# Each service sets only its start command (see backend/README.md, "Deploying to Railway").
# Local development keeps backend/Dockerfile (docker compose), which has no frontend.

FROM node:22-slim AS portfolio
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build:live

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=5 \
    FRONTEND_DIST=/srv/frontend/dist
WORKDIR /srv
COPY backend/requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r /srv/backend/requirements.txt
COPY backend/ /srv/backend/
COPY --from=portfolio /app/frontend/dist /srv/frontend/dist

# Run from /srv so imports are always `backend.*` (keeps backend/logging from shadowing stdlib).
# web: this default. Pre-deploy (web only): alembic -c backend/alembic.ini upgrade head
CMD ["sh", "-c", "exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
