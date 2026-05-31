import re

from domain.chat import ChatMessage
from domain.intent import QueryIntent

_SUMMARIZE_PATTERNS = (
    re.compile(r"\bsummarize\b", re.I),
    re.compile(r"\bsummary\b", re.I),
    re.compile(r"\brecap\b", re.I),
    re.compile(r"\bour discussion\b", re.I),
    re.compile(r"\bwhat did we (talk|discuss)\b", re.I),
    re.compile(r"\bcan you summarize\b", re.I),
    re.compile(r"\bsummarize that\b", re.I),
)

_COMPARE_PATTERNS = (
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\bdifference(s)?\b", re.I),
    re.compile(r"\bdiffer(s|ent)?\b", re.I),
    re.compile(r"\bvs\.?\b", re.I),
    re.compile(r"\bversus\b", re.I),
    re.compile(r"\bbetter than\b", re.I),
)

_HOW_TO_PATTERNS = (
    re.compile(r"^how do i\b", re.I),
    re.compile(r"^how to\b", re.I),
    re.compile(r"\bhow can i\b", re.I),
    re.compile(r"\bsteps to\b", re.I),
    re.compile(r"\bset up\b", re.I),
    re.compile(r"\bconfigure\b", re.I),
    re.compile(r"\bbest way to\b", re.I),
)

_TROUBLESHOOT_PATTERNS = (
    re.compile(r"\btimeout(ing|s)?\b", re.I),
    re.compile(r"\btiming out\b", re.I),
    re.compile(r"\berror(s)?\b", re.I),
    re.compile(r"\bfailing\b", re.I),
    re.compile(r"\bnot working\b", re.I),
    re.compile(r"\bissue(s)?\b", re.I),
    re.compile(r"\bproblem(s)?\b", re.I),
    re.compile(r"\btroubleshoot\b", re.I),
    re.compile(r"\bdebug\b", re.I),
)

_EXPLAIN_PATTERNS = (
    re.compile(r"^what is\b", re.I),
    re.compile(r"^what are\b", re.I),
    re.compile(r"\bexplain\b", re.I),
    re.compile(r"\bdescribe\b", re.I),
    re.compile(r"\btell me about\b", re.I),
)


class IntentClassifier:
    """Deterministic intent classification from query + conversation context."""

    def classify(self, query: str, history: list[ChatMessage] | None = None) -> QueryIntent:
        text = query.strip()
        if not text:
            return QueryIntent.EXPLAIN

        if self._matches_any(_SUMMARIZE_PATTERNS, text):
            return QueryIntent.SUMMARIZE_CONVERSATION

        if history and self._is_memory_summary_request(text):
            return QueryIntent.SUMMARIZE_CONVERSATION

        if self._matches_any(_COMPARE_PATTERNS, text):
            return QueryIntent.COMPARE

        if self._matches_any(_TROUBLESHOOT_PATTERNS, text):
            return QueryIntent.TROUBLESHOOT

        if self._matches_any(_HOW_TO_PATTERNS, text):
            return QueryIntent.HOW_TO

        if self._matches_any(_EXPLAIN_PATTERNS, text):
            return QueryIntent.EXPLAIN

        return QueryIntent.EXPLAIN

    @staticmethod
    def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    @staticmethod
    def _is_memory_summary_request(text: str) -> bool:
        lowered = text.lower()
        return (
            "summarize" in lowered or "summary" in lowered or "recap" in lowered
        ) and len(text.split()) <= 8
