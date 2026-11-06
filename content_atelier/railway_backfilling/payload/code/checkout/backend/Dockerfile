FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=America/Chicago HF_HOME=/models
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend_pipeline ./backend_pipeline
COPY migrations ./migrations
RUN useradd --create-home --uid 10001 atelier && mkdir /artifacts /models && chown atelier:atelier /artifacts /models
USER atelier
EXPOSE 8000
CMD ["uvicorn", "backend_pipeline.api:app", "--host", "0.0.0.0", "--port", "8000"]
