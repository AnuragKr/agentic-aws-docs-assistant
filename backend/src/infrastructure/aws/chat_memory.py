from datetime import datetime, timezone

from config.logging import ConfigurationError, get_logger
from config.utils import with_retry
from infrastructure.aws.session import get_dynamodb_table

from domain.chat import ChatMessage

logger = get_logger(__name__)


class DynamoDBChatMemoryStore:
    """Persists conversation turns keyed by session_id."""

    def __init__(self, table_name: str, region: str, *, max_messages: int = 20) -> None:
        if not table_name:
            raise ConfigurationError("CHAT_MEMORY_TABLE is not configured")
        self._table = get_dynamodb_table(region, table_name)
        self._max_messages = max_messages

    @with_retry()
    def get_history(self, session_id: str) -> list[ChatMessage]:
        response = self._table.get_item(Key={"session_id": session_id})
        item = response.get("Item") or {}
        raw_messages = item.get("messages") or []
        return [ChatMessage.model_validate(message) for message in raw_messages]

    @with_retry()
    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> list[ChatMessage]:
        history = self.get_history(session_id)
        history.extend(
            [
                ChatMessage(role="user", content=user_message),
                ChatMessage(role="assistant", content=assistant_message),
            ]
        )
        trimmed = history[-self._max_messages :]
        self._table.put_item(
            Item={
                "session_id": session_id,
                "messages": [message.model_dump() for message in trimmed],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("chat_memory_saved", session_id=session_id, message_count=len(trimmed))
        return trimmed
