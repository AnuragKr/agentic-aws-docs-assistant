resource "aws_dynamodb_table" "chat_memory" {

  name = "${local.name_prefix}-memory"

  billing_mode = "PAY_PER_REQUEST"

  hash_key = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }
}