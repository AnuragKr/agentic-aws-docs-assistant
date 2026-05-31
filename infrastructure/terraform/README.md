# Terraform

Single **public EC2** runs Streamlit (`:8501`) and FastAPI (`:8000` on localhost). The instance IAM role reaches S3, OpenSearch, DynamoDB, and Bedrock.

```
Internet → EC2 (public)
              ├── :8501 Streamlit (internet)
              ├── :8000 FastAPI (localhost only)
              ├── S3 (raw + processed)
              ├── OpenSearch
              ├── DynamoDB
              └── Bedrock
```

## Apply

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars   # first time only
terraform init
terraform plan
terraform apply
```

`terraform.tfvars` in **this directory** is loaded automatically — no `-var-file` needed.

## On the EC2 host

```bash
cd ~/agentic-aws-docs-assistant   # or your clone path
git pull
cd backend && uv sync

# Verify IAM instance profile (do NOT use sudo)
uv run python scripts/check_aws.py

# Ingestion
uv run python run_ingestion.py --force-reprocess --max-documents 1
```

- Streamlit `frontend/.env`: `API_BASE_URL=http://127.0.0.1:8000`
- FastAPI `backend/.env`: use `terraform output` for buckets, OpenSearch, DynamoDB; `OPENSEARCH_AUTH_MODE=aws_sigv4`
- Do **not** set empty `AWS_ACCESS_KEY_ID=` in `.env` — that blocks the instance profile
- Run as `ubuntu`, not `root` / `sudo`

URL: `terraform output streamlit_url`

### Docker on EC2

```bash
cd ~/agentic-aws-docs-assistant
git pull

# Configure env from terraform output
cp backend/.env.example backend/.env   # edit with real values
cp frontend/.env.example frontend/.env

# Build and run (API on localhost:8000, Streamlit on :8501)
docker compose up -d --build

# First start may take several minutes (reranker download). Check logs:
docker compose logs -f backend

# Optional: run ingestion in container (uses instance profile)
docker compose --profile ingestion run --rm ingestion --force-reprocess --max-documents 1
```

Do **not** pass `sudo` — it breaks the instance profile inside containers on some setups.
Do **not** set empty `AWS_ACCESS_KEY_ID` in `backend/.env`.

### EC2 troubleshooting

| Symptom | Fix |
|--------|-----|
| `AWS credentials not found` | Attach instance profile; `terraform apply`; avoid `sudo` |
| Empty keys in `.env` | Remove `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` lines |
| OpenSearch 403 | `terraform apply` (access policy + IAM); wait for domain `Active` |
| Old code on host | `git pull` && `uv sync` |
