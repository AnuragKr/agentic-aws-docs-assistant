# Frontend — Streamlit

## uv (recommended)

```bash
uv sync
cp .env.example .env
uv run streamlit run app/main.py
```

## pip

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

## Docker

```bash
docker build -t aws-docs-streamlit .
docker run --rm -p 8501:8501 --env-file .env \
  -e API_BASE_URL=http://host.docker.internal:8000 \
  aws-docs-streamlit
```

## Docker Compose

From repo root: `docker compose up --build` (uses `API_BASE_URL=http://backend:8000`).
