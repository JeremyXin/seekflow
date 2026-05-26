import pytest

from seekflow.models import ProviderConfig
from seekflow.providers.playwright_provider import PlaywrightProvider


@pytest.mark.asyncio
async def test_playwright_availability_is_import_based(mocker) -> None:
    mocker.patch("seekflow.providers.playwright_provider.importlib.import_module", return_value=object())
    provider = PlaywrightProvider(ProviderConfig(enabled=True))
    assert await provider.is_available() is True
