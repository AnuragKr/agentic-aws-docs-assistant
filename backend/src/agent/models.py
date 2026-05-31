from pydantic import BaseModel, Field

from domain.chat import ChatMessage
from generation.models import SourceReference


class AgentResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    external_search_used: bool = False


class AgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
