class GenerationError(Exception):
    """Base error for the generation layer."""


class GenerationTimeoutError(GenerationError):
    """Raised when Bedrock generation exceeds the configured timeout."""


class GenerationProviderError(GenerationError):
    """Raised when the LLM provider returns an error."""

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
