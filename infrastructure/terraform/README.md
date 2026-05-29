# Terraform — AWS infrastructure

Provisions core resources for the documentation assistant ingestion pipeline:

- **S3** — documentation source bucket (versioned, encrypted)
- **OpenSearch** — vector index domain (HTTPS, fine-grained access)
- **IAM** — ingestion role (S3 read, OpenSearch HTTP, Bedrock invoke)

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- AWS credentials configured (`aws configure` or environment variables)

## Usage

Variables live in `infrastructure/terraform.tfvars` (not in this directory). From the repo root:

```bash
cp infrastructure/terraform.tfvars.example infrastructure/terraform.tfvars
# Edit infrastructure/terraform.tfvars (bucket name, passwords)

cd infrastructure/terraform
terraform init
terraform plan -var-file=../terraform.tfvars
terraform apply -var-file=../terraform.tfvars
```

After apply, wire `backend/.env` from outputs:

```bash
terraform output s3_bucket_name
terraform output opensearch_endpoint
```

```env
S3_BUCKET=<s3_bucket_name>
OPENSEARCH_HOST=<opensearch_endpoint without https://>
OPENSEARCH_AUTH_MODE=aws_sigv4
OPENSEARCH_INDEX=aws-docs
```

For local OpenSearch with basic auth, skip this module and use Docker instead.

## State

By default Terraform uses local state (`terraform.tfstate`) in this directory. For teams, configure a remote backend (S3 + DynamoDB) in `main.tf`.
