FROM python:3.12-slim-bookworm
# ATELIER_ARTIFACT_ROOT: the local artifact folder (and the llm_runs fallback file) is /artifacts, which the app user owns;
# /app is read-only to it. On the platform the artifact store is the bucket (ATELIER_ARTIFACT_STORE=s3).
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=America/Chicago HF_HOME=/models ATELIER_ARTIFACT_ROOT=/artifacts
# The PostgreSQL 17 client (pg_dump, pg_restore, psql) from the PostgreSQL project's repository, for the nightly dump and
# restore check (backend_pipeline.backup, 6.B6) and restores on the platform: Debian's own client is too old for a PG 17 server.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgomp1 tzdata ca-certificates curl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-17 \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend_pipeline ./backend_pipeline
# The week's review document's Word template (5.B14) ships in the image, made from the package: no office file is committed
# outside research/ (R48), so it is built here, before the app user (who cannot write /app) takes over.
RUN python -m backend_pipeline.briefs.review_template
COPY migrations ./migrations
# The knowledge base the strategist and brief writer load (E.B11 e); archived versions replay saved runs.
COPY knowledge_base ./knowledge_base
RUN useradd --create-home --uid 10001 atelier && mkdir /artifacts /models && chown atelier:atelier /artifacts /models
USER atelier
EXPOSE 8000
# The platform names the port in $PORT (Railway); 8000 locally. backend_pipeline.serve runs uvicorn on one socket that takes
# IPv6 and IPv4: Railway's private network, which the Frontend uses to reach the API, is IPv6 only, and `uvicorn --host ::`
# alone would answer IPv6 only. The workers and the scheduler override this command.
CMD ["python", "-m", "backend_pipeline.serve"]
