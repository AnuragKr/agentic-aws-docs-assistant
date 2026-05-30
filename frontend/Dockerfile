FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_BASE_URL=http://backend:8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"

CMD ["streamlit", "run", "app/main.py", \
    "--server.address", "0.0.0.0", \
    "--server.port", "8501", \
    "--server.headless", "true", \
    "--browser.gatherUsageStats", "false"]
