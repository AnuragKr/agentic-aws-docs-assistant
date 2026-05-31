from unittest.mock import MagicMock

import pytest

from config.settings import Settings
from domain.models import RetrievedChunk
from generation.exceptions import GenerationError
from generation.models import GenerationRequest
from generation.prompt_builder import PromptBuilder
from generation.service import GenerationService


def test_generation_service_returns_answer_and_sources() -> None:
    provider = MagicMock()
    provider.model_id = "meta.llama3-8b-instruct-v1:0"
    provider.generate.return_value = "Use AWS Organizations for centralized governance."

    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Organizations helps manage accounts.",
            score=0.9,
            document_title="Well-Architected",
            section="Organization",
            page_number=12,
        )
    ]

    service = GenerationService(
        provider=provider,
        prompt_builder=PromptBuilder(context_max_tokens=2000),
        settings=Settings(),
    )
    response = service.generate(
        GenerationRequest(question="How to govern accounts?", retrieved_chunks=chunks)
    )

    assert "Organizations" in response.answer
    assert response.model_id == provider.model_id
    assert len(response.sources) == 1
    assert response.sources[0].document_name == "Well-Architected"
    assert response.sources[0].page_number == 12
    provider.generate.assert_called_once()


def test_generation_service_rejects_empty_question() -> None:
    service = GenerationService(
        provider=MagicMock(),
        prompt_builder=PromptBuilder(),
        settings=Settings(),
    )
    with pytest.raises(GenerationError):
        service.generate(GenerationRequest(question="  ", retrieved_chunks=[]))
