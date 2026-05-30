# Backend — FastAPI

## uv (recommended)

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## pip

```bash
pip install -r requirements.txt
export PYTHONPATH=src
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker

```bash
docker build -t aws-docs-backend .
docker run --rm -p 8000:8000 --env-file .env aws-docs-backend
```

## Tests

```bash
uv sync --group dev
uv run pytest
```
