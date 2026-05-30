variable "aws_region" {}
variable "project_name" {}
variable "environment" {}

variable "key_pair_name" {}

variable "raw_bucket_name" {}
variable "processed_bucket_name" {}

variable "ec2_instance_type" {
  default = "t3.medium"
}

variable "ssh_allowed_cidr" {
  description = "CIDR for SSH (empty = no SSH rule)"
  default     = ""
}

variable "opensearch_instance_type" {
  default = "t3.small.search"
}

variable "opensearch_instance_count" {
  default = 1
}

variable "opensearch_ebs_volume_size" {
  default = 20
}
