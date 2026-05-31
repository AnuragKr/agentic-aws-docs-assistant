resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/${var.project_name}/${var.environment}/ingestion"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "system" {
  name              = "/${var.project_name}/${var.environment}/system"
  retention_in_days = 14

  tags = local.common_tags
}
