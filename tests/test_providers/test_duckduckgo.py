import pytest

from seekflow.models import ProviderConfig, SearchResult
from seekflow.providers import duckduckgo  # noqa: F401
from seekflow.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_duckduckgo_provider_returns_results(mocker) -> None:
    fake_results = [
        {"href": "https://example.com", "title": "Example", "body": "Snippet"},
    ]
    mocker.patch("seekflow.providers.duckduckgo.DDGS.text", return_value=fake_results)
    provider = ProviderRegistry.get("duckduckgo", ProviderConfig(enabled=True))
    results = await provider.search("python", num_results=5)
    assert results == [
        SearchResult(
            url="https://example.com",
            title="Example",
            snippet="Snippet",
            provider="duckduckgo",
        )
    ]
