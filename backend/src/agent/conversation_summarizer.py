from config.logging import get_logger
from generation.providers.base import GenerationProvider

from domain.chat import ChatMessage

logger = get_logger(__name__)

_SUMMARY_SYSTEM = """You are an AWS Solutions Architect assistant summarizing a prior conversation.

Use ONLY the conversation history provided.
Do not invent AWS topics that were not discussed.

Structure your response with these sections:

## Summary of Discussion
## Key Takeaways
## Recommended Next Steps"""

_SUMMARY_USER = """Conversation history:
{history}

Summarize the AWS topics discussed above."""


class ConversationSummarizer:
    """Generate summaries from chat history — no retrieval."""

    def __init__(self, provider: GenerationProvider) -> None:
        self._provider = provider

    def summarize(self, history: list[ChatMessage]) -> str:
        if not history:
            return (
                "We have not discussed any AWS topics yet. "
                "Ask a question about an AWS service to start the conversation."
            )

        history_block = "\n".join(
            f"{message.role}: {message.content}" for message in history[-20:]
        )
        user_prompt = _SUMMARY_USER.format(history=history_block)
        answer = self._provider.generate(_SUMMARY_SYSTEM, user_prompt).strip()
        logger.info("conversation_summarized", history_messages=len(history))
        return answer
