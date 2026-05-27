# Terraform — AWS infrastructure

Provisions core resources for the documentation assistant ingestion pipeline:

- **S3** — documentation source bucket (versioned, encrypted)
- **OpenSearch** — vector index domain (HTTPS, fine-grained access)
- **IAM** — ingestion role (S3 read, OpenSearch HTTP, Bedrock invoke)

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- AWS credentials configured (`aws configure` or environment variables)

## Usage

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars (bucket name, passwords)

terraform init
terraform plan
terraform apply
```

After apply, wire the API `.env` from outputs:

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

By default Terraform uses local state (`terraform.tfstate`). For teams, configure a remote backend (S3 + DynamoDB) in `versions.tf`.
