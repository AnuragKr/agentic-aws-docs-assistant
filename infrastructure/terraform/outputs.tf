output "ec2_public_ip" {
  value = aws_instance.app.public_ip
}

output "streamlit_url" {
  description = "Public UI (FastAPI stays on 127.0.0.1:8000)"
  value       = "http://${aws_instance.app.public_ip}:8501"
}

output "raw_bucket" {
  value = aws_s3_bucket.raw_docs.bucket
}

output "processed_bucket" {
  value = aws_s3_bucket.processed_docs.bucket
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.vector_store.endpoint
}

output "dynamodb_table" {
  value = aws_dynamodb_table.chat_memory.name
}

output "document_registry_table" {
  value = aws_dynamodb_table.document_registry.name
}

output "cloudwatch_ingestion_log_group" {
  description = "CloudWatch log group for ingestion app logs"
  value       = aws_cloudwatch_log_group.ingestion.name
}

output "cloudwatch_system_log_group" {
  description = "CloudWatch log group for EC2 syslog / OOM killer (via CloudWatch agent)"
  value       = aws_cloudwatch_log_group.system.name
}
