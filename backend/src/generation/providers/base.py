from abc import ABC, abstractmethod


class GenerationProvider(ABC):
    """LLM provider interface — invoke only, no retrieval logic."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return model text completion."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Configured model identifier."""
