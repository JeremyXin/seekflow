class SeekFlowError(Exception):
    """Base exception for SeekFlow."""


class ProviderNotConfiguredError(SeekFlowError):
    """Raised when a provider is unavailable or misconfigured."""


class NoResultsError(SeekFlowError):
    """Raised when a search returns no results."""


class LLMError(SeekFlowError):
    """Raised when the configured LLM cannot complete a request."""
