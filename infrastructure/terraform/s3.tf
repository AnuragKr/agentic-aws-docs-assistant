resource "aws_s3_bucket" "raw_docs" {
  bucket = var.raw_bucket_name
  tags   = merge(local.common_tags, { Name = "raw-docs" })
}

resource "aws_s3_bucket" "processed_docs" {
  bucket = var.processed_bucket_name
  tags   = merge(local.common_tags, { Name = "processed-docs" })
}

resource "aws_s3_bucket_public_access_block" "raw_docs" {
  bucket = aws_s3_bucket.raw_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed_docs" {
  bucket = aws_s3_bucket.processed_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
