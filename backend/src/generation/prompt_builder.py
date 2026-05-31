from config.token_utils import count_tokens, get_token_encoder
from domain.models import RetrievedChunk

SYSTEM_PROMPT = """You are an AWS Solutions Architect assistant.

Use ONLY the provided context to answer.

Do not use external knowledge.

If the answer is not available in the context, explicitly state that the information could not be found in the retrieved AWS documentation.

Provide concise, accurate, and actionable answers.

Always include source references."""

USER_PROMPT_TEMPLATE = """Context:
{context}

Question:
{question}

Instructions:

1. Answer using only the provided context.

2. Provide a concise explanation.

3. Include key recommendations when applicable.

4. Cite the source documents used.

5. If information is missing, say so explicitly."""


class PromptBuilder:
    """Builds system and user prompts from reranked retrieval chunks."""

    def __init__(self, context_max_tokens: int = 4500) -> None:
        self._context_max_tokens = context_max_tokens
        self._encoder = get_token_encoder()

    def build(self, question: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
        context = self.build_context(chunks)
        user_prompt = USER_PROMPT_TEMPLATE.format(context=context, question=question.strip())
        return SYSTEM_PROMPT, user_prompt

    def build_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No documentation context was retrieved."

        blocks: list[str] = []
        used_tokens = 0

        for chunk in chunks:
            block = self._format_chunk(chunk)
            block_tokens = count_tokens(block, self._encoder)
            if used_tokens + block_tokens > self._context_max_tokens:
                break
            blocks.append(block)
            used_tokens += block_tokens

        return "\n\n---\n\n".join(blocks) if blocks else "No documentation context was retrieved."

    def estimate_prompt_tokens(self, question: str, chunks: list[RetrievedChunk]) -> int:
        system, user = self.build(question, chunks)
        return count_tokens(f"{system}\n\n{user}", self._encoder)

    @staticmethod
    def _format_chunk(chunk: RetrievedChunk) -> str:
        document_name = chunk.document_title or chunk.title or chunk.source_file or chunk.document_id
        section_title = chunk.section or chunk.subsection or "—"
        page = chunk.page_number if chunk.page_number is not None else "—"
        return (
            f"Source: {document_name}\n"
            f"Section: {section_title}\n"
            f"Page: {page}\n\n"
            f"Content:\n{chunk.content.strip()}"
        )
