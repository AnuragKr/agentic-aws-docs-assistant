# Frontend — Streamlit UI

Simple Streamlit app that calls the FastAPI ingestion API. No Node/React required.

## Run

Start the API from the repo root:

```bash
uv sync --group ui
uv run uvicorn app.main:app --reload
```

In another terminal:

```bash
uv run streamlit run frontend/app.py
```

Open http://localhost:8501

## Configuration

Optional environment variable:

```bash
export API_BASE_URL=http://127.0.0.1:8000
```

Or set the API URL in the sidebar of the app.
