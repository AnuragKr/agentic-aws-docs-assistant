output "s3_bucket_name" {
  description = "Documentation source bucket"
  value       = aws_s3_bucket.docs.id
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.docs.arn
}

output "opensearch_endpoint" {
  description = "OpenSearch HTTPS endpoint (use in OPENSEARCH_HOST)"
  value       = aws_opensearch_domain.main.endpoint
}

output "opensearch_domain_arn" {
  value = aws_opensearch_domain.main.arn
}

output "opensearch_dashboard_endpoint" {
  value = aws_opensearch_domain.main.dashboard_endpoint
}

output "ingestion_role_arn" {
  description = "IAM role for the ingestion service (attach to EC2/ECS/Lambda as needed)"
  value       = aws_iam_role.ingestion.arn
}
