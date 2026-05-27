## AWS Documentation Intelligence Assistant

An Agentic AI-powered chatbot that enables users to interact with AWS documentation using natural language queries.

## Development (uv)

Prerequisites: [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
# Install dependencies (creates .venv)
uv sync --dev

# Copy environment template
cp .env.example .env

# Run API
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest
```

API endpoints:

- `GET /health`
- `POST /ingestion/start`
- `POST /ingestion/reindex`
- `GET /ingestion/status?job_id=<uuid>`

### Project structure

```
agentic-aws-docs-assistant/
├── src/app/                # FastAPI backend (Python / uv)
├── frontend/               # Streamlit UI
├── terraform/              # AWS: S3, OpenSearch, IAM
└── tests/
```

Backend (`src/app/`):

```
src/app/
├── main.py
├── api/                    # routes, schemas, deps
├── core/                   # config, container, exceptions
├── ingestion/              # domain, ports, pipeline, loaders, …
├── infrastructure/         # AWS & OpenSearch clients
└── observability/
```

See [frontend/README.md](frontend/README.md) and [terraform/README.md](terraform/README.md) for UI and infrastructure setup.

### Frontend (Streamlit UI)

```bash
uv sync --group ui
uv run streamlit run frontend/app.py
```

Opens http://localhost:8501 (calls FastAPI on port 8000; set `API_BASE_URL` if needed).

### Terraform (AWS)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

Provisions S3 (docs bucket), OpenSearch domain, and an ingestion IAM role.

### Ingestion pipeline

```
S3 → parse (txt/md/html) → preprocess → metadata → hierarchical chunk → embed → OpenSearch
```

Set `S3_BUCKET` (and optionally `S3_PREFIX`) in `.env` when your bucket is ready. Until then, jobs fail fast with a clear configuration error.

Run unit tests (no AWS required):

```bash
uv run pytest tests/unit -q
```

The application leverages Retrieval-Augmented Generation (RAG), hybrid search, and agentic workflows to provide grounded, context-aware responses based on AWS official documentation.

The project is designed as a scalable AWS-native solution demonstrating modern LLM application architecture and clean engineering practices.

## Objectives

The system aims to demonstrate:

+ LLM-based application design
+ Agentic workflow orchestration
+ Retrieval-Augmented Generation (RAG)
+ Natural language query handling
+ AWS documentation integration
+ Scalable and modular architecture

## Scope

The initial version focuses on a text-based conversational experience.

### Included

+ AWS documentation ingestion pipeline
+ Vector indexing and retrieval
+ Hybrid search (semantic + keyword)
+ Query expansion and agentic retrieval workflows
+ Context-aware response generation
+ Citation support
+ Conversational memory
+ AWS-native deployment

### Out of Scope

The following capabilities are intentionally excluded from the MVP:

+ image/table understanding
+ multimodal retrieval
+ voice interaction
+ infrastructure execution
autonomous multi-agent systems

These may be added in future iterations.

## High-Level Workflow

```
User Query
    ↓
Query Understanding
    ↓
Agentic Retrieval Orchestrator
    ↓
Hybrid Retrieval Layer
    ↓
Context Selection & Reranking
    ↓
LLM Generation
    ↓
Grounded Response + Citations

```
