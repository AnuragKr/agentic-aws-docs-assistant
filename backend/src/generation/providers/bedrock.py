import json
from typing import Any

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, ReadTimeoutError

from config.settings import Settings
from generation.exceptions import (
    GenerationProviderError,
    GenerationTimeoutError,
)
from generation.providers.base import GenerationProvider
from infrastructure.aws.session import get_boto_session

_RETRYABLE_ERROR_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
    "InternalServerException",
}


def is_llama_model(model_id: str) -> bool:
    normalized = model_id.lower()
    return normalized.startswith("meta.") or "llama" in normalized


def _llama3_turn(role: str, content: str) -> str:
    return f"<|start_header_id|>{role}<|end_header_id|>\n\n{content.strip()}<|eot_id|>"


def format_llama3_prompt(system_prompt: str, user_prompt: str) -> str:
    """Meta Llama 3 instruct chat template for Bedrock invoke_model."""
    return (
        "<|begin_of_text|>"
        + _llama3_turn("system", system_prompt)
        + _llama3_turn("user", user_prompt)
        + "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


class BedrockGenerationProvider(GenerationProvider):
    """Amazon Bedrock Runtime — supports Anthropic Claude and Meta Llama instruct models."""

    def __init__(self, settings: Settings) -> None:
        self._model_id = settings.bedrock_model_id
        self._use_llama = is_llama_model(self._model_id)
        self._max_tokens = settings.generation_max_tokens
        self._temperature = settings.generation_temperature
        self._top_p = settings.generation_top_p
        self._client = get_boto_session(settings.bedrock_region).client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            config=Config(
                retries={"max_attempts": settings.generation_max_retries, "mode": "adaptive"},
                read_timeout=settings.generation_timeout_seconds,
                connect_timeout=settings.generation_timeout_seconds,
            ),
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        body = self._build_request_body(system_prompt, user_prompt)
        try:
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except ReadTimeoutError as exc:
            raise GenerationTimeoutError(
                f"Bedrock generation timed out after {self._client.meta.config.read_timeout}s"
            ) from exc
        except ClientError as exc:
            raise self._map_client_error(exc) from exc
        except BotoCoreError as exc:
            raise GenerationProviderError(f"Bedrock request failed: {exc}") from exc

        return self._parse_response(response["body"].read())

    def _build_request_body(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self._use_llama:
            return {
                "prompt": format_llama3_prompt(system_prompt, user_prompt),
                "max_gen_len": self._max_tokens,
                "temperature": self._temperature,
                "top_p": self._top_p,
            }
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

    def _parse_response(self, raw_body: bytes) -> str:
        payload = json.loads(raw_body)
        if self._use_llama:
            answer = (payload.get("generation") or "").strip()
        else:
            content = payload.get("content") or []
            text_parts = [
                block.get("text", "") for block in content if block.get("type") == "text"
            ]
            answer = "".join(text_parts).strip()

        if not answer:
            raise GenerationProviderError("Bedrock returned an empty response")
        return answer

    def _map_client_error(self, exc: ClientError) -> Exception:
        error = exc.response.get("Error", {})
        code = error.get("Code", "Unknown")
        message = error.get("Message", str(exc))

        if code in {"AccessDeniedException", "AccessDenied"}:
            return GenerationProviderError(
                f"Bedrock access denied: {message}",
                error_code=code,
            )
        if code in {"ValidationException", "ValidationError"}:
            return GenerationProviderError(
                f"Bedrock validation error: {message}",
                error_code=code,
            )
        if code in _RETRYABLE_ERROR_CODES:
            return GenerationProviderError(
                f"Bedrock service error ({code}): {message}",
                error_code=code,
            )
        return GenerationProviderError(f"Bedrock error ({code}): {message}", error_code=code)
