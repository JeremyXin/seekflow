import pytest

from seekflow.models import ProviderConfig
from seekflow.providers.brave import BraveSearchProvider


@pytest.mark.asyncio
async def test_brave_requires_api_key() -> None:
    provider = BraveSearchProvider(ProviderConfig(enabled=True, api_key=None))
    assert await provider.is_available() is False
