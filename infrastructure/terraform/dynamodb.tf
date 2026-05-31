resource "aws_dynamodb_table" "chat_memory" {

  name = "${local.name_prefix}-memory"

  billing_mode = "PAY_PER_REQUEST"

  hash_key = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "document_registry" {
  name         = "${local.name_prefix}-document-registry"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_key"

  attribute {
    name = "source_key"
    type = "S"
  }

  tags = local.common_tags
}