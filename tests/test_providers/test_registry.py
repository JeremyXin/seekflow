from seekflow.models import ProviderConfig
from seekflow.providers import duckduckgo  # noqa: F401
from seekflow.providers.registry import ProviderRegistry


def test_registry_returns_registered_provider() -> None:
    provider = ProviderRegistry.get("duckduckgo", ProviderConfig(enabled=True))
    assert provider.name == "duckduckgo"
