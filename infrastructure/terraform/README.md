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

- Streamlit `frontend/.env`: `API_BASE_URL=http://127.0.0.1:8000`
- FastAPI `backend/.env`: use `terraform output` for buckets, OpenSearch, DynamoDB; `OPENSEARCH_AUTH_MODE=aws_sigv4`

URL: `terraform output streamlit_url`
