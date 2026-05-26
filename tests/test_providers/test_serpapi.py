import pytest

from seekflow.models import ProviderConfig
from seekflow.providers.serpapi import SerpApiProvider


@pytest.mark.asyncio
async def test_serpapi_requires_api_key() -> None:
    provider = SerpApiProvider(ProviderConfig(enabled=True, api_key=""))
    assert await provider.is_available() is False
