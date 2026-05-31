from config.logging import get_logger
from config.settings import Settings
from generation.providers.base import GenerationProvider

from domain.intent import QueryIntent
from domain.chat import ChatMessage

logger = get_logger(__name__)

_REWRITE_SYSTEM = """You rewrite follow-up questions into standalone AWS queries.

Rules:
- Resolve pronouns and references using the conversation.
- For comparison follow-ups, name both AWS services explicitly.
- For summary follow-ups about prior answers, rewrite as a conversation-summary request.
- Output ONLY the rewritten query — no explanation."""

_REWRITE_USER = """Conversation (most recent last):
{history}

Latest user message:
{query}

Intent: {intent}

Rewritten standalone query:"""


class ConversationAwareQueryRewriter:
    """Rewrite follow-ups using the last N conversation turns."""

    def __init__(self, provider: GenerationProvider, settings: Settings) -> None:
        self._provider = provider
        self._turns = settings.conversation_rewrite_turns

    def rewrite(
        self,
        query: str,
        history: list[ChatMessage],
        *,
        intent: QueryIntent,
    ) -> str:
        query = query.strip()
        if not query:
            return query

        if intent == QueryIntent.SUMMARIZE_CONVERSATION:
            return self._rewrite_summary_request(query, history)

        if not history:
            return query

        recent = history[-(self._turns * 2) :]
        history_block = "\n".join(f"{message.role}: {message.content}" for message in recent)
        user_prompt = _REWRITE_USER.format(
            history=history_block,
            query=query,
            intent=intent.value,
        )

        try:
            rewritten = self._provider.generate(_REWRITE_SYSTEM, user_prompt).strip()
            if rewritten:
                logger.info(
                    "query_rewritten",
                    intent=intent.value,
                    original_len=len(query),
                    rewritten_len=len(rewritten),
                )
                return rewritten
        except Exception:
            logger.warning("query_rewrite_failed", query_len=len(query), intent=intent.value)

        return self._fallback_rewrite(query, history, intent)

    @staticmethod
    def _rewrite_summary_request(query: str, history: list[ChatMessage]) -> str:
        if not history:
            return query
        topics = []
        for message in history[-6:]:
            if message.role == "user" and message.content.strip():
                topics.append(message.content.strip())
        if topics:
            joined = "; ".join(topics[-3:])
            return f"Summarize our AWS discussion covering: {joined}"
        return query

    @staticmethod
    def _fallback_rewrite(query: str, history: list[ChatMessage], intent: QueryIntent) -> str:
        if intent != QueryIntent.COMPARE or not history:
            return query

        last_user = next(
            (message.content for message in reversed(history) if message.role == "user"),
            "",
        )
        if last_user and ("it" in query.lower() or "different" in query.lower()):
            return f"{query.strip()} (context: previous topic was {last_user})"
        return query
