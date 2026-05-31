# syntax=docker/dockerfile:1
# Backend — FastAPI ingestion, search, RAG generation (CPU-only ML stack).
# EC2: uses instance profile via IMDS — do not bake AWS keys into the image.

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# libgomp1: PyTorch CPU; curl: healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# CPU-only PyTorch via extra index; single pip resolve (no duplicate torch).
COPY requirements.txt ./
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt \
    && pip check

COPY src ./src
COPY run_ingestion.py .
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.cache/huggingface \
    && chown -R appuser:appuser /app

WORKDIR /app/src
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
