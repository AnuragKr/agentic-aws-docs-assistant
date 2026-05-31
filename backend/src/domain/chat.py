from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(description="user or assistant")
    content: str = Field(min_length=1)
