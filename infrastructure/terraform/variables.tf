variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix for resource names"
  type        = string
  default     = "aws-docs-assistant"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "docs_bucket_name" {
  description = "S3 bucket name for AWS documentation files (must be globally unique)"
  type        = string
}

variable "opensearch_instance_type" {
  description = "OpenSearch data node instance type"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch data nodes"
  type        = number
  default     = 1
}

variable "opensearch_ebs_volume_size" {
  description = "EBS volume size (GB) per OpenSearch node"
  type        = number
  default     = 20
}

variable "opensearch_master_user" {
  description = "Fine-grained access master username"
  type        = string
  default     = "admin"
}

variable "opensearch_master_password" {
  description = "Fine-grained access master password"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
