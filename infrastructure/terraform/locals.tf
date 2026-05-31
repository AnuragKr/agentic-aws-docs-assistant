locals {

  name_prefix = "${var.project_name}-${var.environment}"

  # OpenSearch domain_name: 3–28 chars, lowercase a-z, 0-9, hyphen
  opensearch_domain_long  = "${local.name_prefix}-vector"
  opensearch_domain_short = substr("${local.name_prefix}-vec", 0, 28)
  opensearch_domain_name = (
    length(local.opensearch_domain_long) <= 28
    ? local.opensearch_domain_long
    : local.opensearch_domain_short
  )

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}