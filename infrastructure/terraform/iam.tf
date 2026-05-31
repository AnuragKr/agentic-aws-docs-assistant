resource "aws_iam_role" "ec2_role" {
  name = "${local.name_prefix}-ec2"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${local.name_prefix}-profile"
  role = aws_iam_role.ec2_role.name

  tags = local.common_tags
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "${local.name_prefix}-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.raw_docs.arn,
          "${aws_s3_bucket.raw_docs.arn}/*",
          aws_s3_bucket.processed_docs.arn,
          "${aws_s3_bucket.processed_docs.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpDelete",
          "es:ESHttpHead",
        ]
        Resource = [
          aws_opensearch_domain.vector_store.arn,
          "${aws_opensearch_domain.vector_store.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
        ]
        Resource = [
          aws_dynamodb_table.chat_memory.arn,
          aws_dynamodb_table.document_registry.arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
        ]
        Resource = [
          "${aws_cloudwatch_log_group.ingestion.arn}:*",
          "${aws_cloudwatch_log_group.system.arn}:*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      },
    ]
  })
}
