import json

from generation.providers.bedrock import (
    BedrockGenerationProvider,
    format_llama3_prompt,
    is_llama_model,
)


def test_is_llama_model_detects_meta_ids() -> None:
    assert is_llama_model("meta.llama3-8b-instruct-v1:0") is True
    assert is_llama_model("anthropic.claude-3-7-sonnet-20250219-v1:0") is False


def test_format_llama3_prompt_uses_chat_template() -> None:
    prompt = format_llama3_prompt("You are helpful.", "What is S3?")
    assert "<|start_header_id|>system<|end_header_id|>" in prompt
    assert "You are helpful." in prompt
    assert "What is S3?" in prompt
    assert "<|start_header_id|>assistant<|end_header_id|>" in prompt


def test_llama_request_body_uses_prompt_and_max_gen_len() -> None:
    from config.settings import Settings

    provider = BedrockGenerationProvider(
        Settings(BEDROCK_MODEL_ID="meta.llama3-8b-instruct-v1:0", GENERATION_MAX_TOKENS=512)
    )
    body = provider._build_request_body("System", "User question")
    assert "prompt" in body
    assert body["max_gen_len"] == 512
    assert "anthropic_version" not in body
    assert "System" in body["prompt"]


def test_llama_response_parsing() -> None:
    from config.settings import Settings

    provider = BedrockGenerationProvider(Settings(BEDROCK_MODEL_ID="meta.llama3-8b-instruct-v1:0"))
    raw = json.dumps({"generation": "AWS Lambda runs code on demand."}).encode()
    assert provider._parse_response(raw) == "AWS Lambda runs code on demand."


def test_claude_request_body_uses_messages_api() -> None:
    from config.settings import Settings

    provider = BedrockGenerationProvider(
        Settings(BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0")
    )
    body = provider._build_request_body("System", "User question")
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["messages"][0]["content"] == "User question"
