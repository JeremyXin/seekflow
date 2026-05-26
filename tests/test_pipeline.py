import pytest

from seekflow.errors import NoResultsError
from seekflow.models import SearchResult
from seekflow.pipeline import SearchPipeline


@pytest.mark.asyncio
async def test_pipeline_happy_path(mocker, app_config) -> None:
    provider = mocker.patch("seekflow.pipeline.ProviderRegistry.get").return_value
    provider.is_available.return_value = True
    provider.search.return_value = [
        SearchResult(
            url="https://example.com",
            title="Example",
            snippet="Snippet",
            provider="duckduckgo",
        )
    ]
    mocker.patch("seekflow.pipeline.extract_content", return_value="Extracted content")
    mocker.patch(
        "seekflow.pipeline.generate_metadata",
        return_value={"summary": "Summary", "tags": ["python"], "category": "programming"},
    )
    mocker.patch("seekflow.pipeline.save_entry")
    mocker.patch(
        "seekflow.pipeline.synthesize_answer",
        return_value=_async_iter(["Part 1 ", "Part 2"]),
    )
    pipeline = SearchPipeline()
    entry = await pipeline.run("python gil", app_config)
    assert entry.summary == "Summary"
    assert entry.category == "programming"


@pytest.mark.asyncio
async def test_pipeline_raises_on_empty_results(mocker, app_config) -> None:
    provider = mocker.patch("seekflow.pipeline.ProviderRegistry.get").return_value
    provider.is_available.return_value = True
    provider.search.return_value = []
    pipeline = SearchPipeline()
    with pytest.raises(NoResultsError):
        await pipeline.run("missing", app_config)


class _AsyncIter:
    def __init__(self, items: list[str]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        value = self._items[self._index]
        self._index += 1
        return value


def _async_iter(items: list[str]) -> _AsyncIter:
    return _AsyncIter(items)
