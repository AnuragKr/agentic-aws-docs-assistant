## AWS Documentation Intelligence Assistant

Agentic AI chatbot for AWS documentation (RAG, hybrid search, AWS-native deployment).

## Repository layout

```
agentic-aws-docs-assistant/
├── backend/          # FastAPI — own pyproject.toml, uv.lock, requirements.txt, .venv
├── frontend/         # Streamlit — own pyproject.toml, uv.lock, requirements.txt, .venv
├── infrastructure/terraform/
├── docker-compose.yml
└── README.md
```

No root `uv.lock` or shared Python env — each app is independent.

| Component | Config | Dependencies |
|-----------|--------|----------------|
| Backend | `backend/.env` | `backend/pyproject.toml` + `uv.lock` |
| Frontend | `frontend/.env` | `frontend/pyproject.toml` + `uv.lock` |
| Infra | `infrastructure/terraform/terraform.tfvars` | Terraform |

## Local development (uv)

### Backend

```bash
cd backend
uv sync              # creates backend/.venv
cp .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Dev tools: `uv sync --group dev`

### Frontend

```bash
cd frontend
uv sync              # creates frontend/.venv (lean — no torch)
cp .env.example .env
uv run streamlit run app/main.py
```

Open http://localhost:8501 — set `API_BASE_URL=http://127.0.0.1:8000` in `frontend/.env`.

## Local development (pip)

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

## Docker Compose

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up -d --build
```

- Streamlit: http://localhost:8501 (on EC2: `http://<public-ip>:8501`)
- FastAPI: http://127.0.0.1:8000 on the host (not exposed on `0.0.0.0`; frontend uses `http://backend:8000` in the compose network)

**Ingestion in Docker:**

```bash
docker compose --profile ingestion run --rm ingestion --force-reprocess --max-documents 3
```

## Infrastructure

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

## Regenerate lockfiles

```bash
cd backend && uv lock
cd frontend && uv lock
```

Optional frozen export: `uv export --frozen -o requirements.txt`
