from config.token_utils import count_tokens, get_token_encoder
from domain.models import RetrievedChunk

from domain.intent import QueryIntent
from generation.intent_prompts import build_system_prompt
from generation.models import ExternalSearchResult

USER_PROMPT_TEMPLATE = """Internal AWS documentation context:
{context}

{external_block}Question:
{question}

Instructions:

1. Answer using only the provided evidence.

2. Prefer internal documentation over external web results.

3. Follow the response structure defined in the system prompt.

4. Do not mention missing information unless the context is completely empty."""


class PromptBuilder:
    """Builds intent-specific prompts from reranked retrieval chunks."""

    def __init__(self, context_max_tokens: int = 4500) -> None:
        self._context_max_tokens = context_max_tokens
        self._encoder = get_token_encoder()

    def build(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        external_results: list[ExternalSearchResult] | None = None,
        *,
        intent: QueryIntent = QueryIntent.EXPLAIN,
    ) -> tuple[str, str]:
        context = self.build_context(chunks)
        external_block = self.build_external_block(external_results or [])
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            external_block=external_block,
            question=question.strip(),
        )
        return build_system_prompt(intent), user_prompt

    def build_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No internal documentation context was retrieved."

        blocks: list[str] = []
        used_tokens = 0

        for chunk in chunks:
            block = self._format_chunk(chunk)
            block_tokens = count_tokens(block, self._encoder)
            if used_tokens + block_tokens > self._context_max_tokens:
                break
            blocks.append(block)
            used_tokens += block_tokens

        if not blocks:
            return "No internal documentation context was retrieved."
        return "\n\n---\n\n".join(blocks)

    def build_external_block(self, external_results: list[ExternalSearchResult]) -> str:
        if not external_results:
            return ""

        lines = ["External AWS web results (fallback only):", ""]
        for index, result in enumerate(external_results, start=1):
            lines.extend(
                [
                    f"[External {index}] {result.title}",
                    f"URL: {result.url}",
                    f"Content: {result.content.strip()}",
                    "",
                ]
            )
        return "\n".join(lines) + "\n"

    def estimate_prompt_tokens(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        external_results: list[ExternalSearchResult] | None = None,
        *,
        intent: QueryIntent = QueryIntent.EXPLAIN,
    ) -> int:
        system, user = self.build(question, chunks, external_results, intent=intent)
        return count_tokens(f"{system}\n\n{user}", self._encoder)

    @staticmethod
    def _format_chunk(chunk: RetrievedChunk) -> str:
        document_name = chunk.document_title or chunk.title or chunk.source_file or chunk.document_id
        section_title = chunk.section or chunk.subsection or "General"
        lines = [
            f"Source: {document_name}",
            f"Section: {section_title}",
        ]
        if chunk.page_number is not None:
            lines.append(f"Page: {chunk.page_number}")
        lines.extend(["", f"Content:\n{chunk.content.strip()}"])
        return "\n".join(lines)
