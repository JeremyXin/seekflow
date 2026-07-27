import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from seekflow.errors import NoResultsError, ProviderNotConfiguredError
from seekflow.models import SearchResult
from seekflow.pipeline import SearchPipeline
from seekflow.workflows.models import Artifact


@pytest.mark.asyncio
async def test_pipeline_happy_path(mocker, app_config) -> None:
    provider = mocker.patch("seekflow.workflows.builtin.ProviderRegistry.get").return_value
    provider.is_available.return_value = True
    provider.search.return_value = [
        SearchResult(
            url="https://example.com",
            title="Example",
            snippet="Snippet",
            provider="duckduckgo",
        )
    ]
    mocker.patch("seekflow.workflows.builtin.extract_content", return_value="Extracted content")
    mocker.patch(
        "seekflow.workflows.builtin.generate_metadata",
        return_value={"summary": "Summary", "tags": ["python"], "category": "programming"},
    )
    mocker.patch("seekflow.workflows.builtin.save_entry")
    mocker.patch(
        "seekflow.workflows.builtin.synthesize_answer",
        return_value=_async_iter(["Part 1 ", "Part 2"]),
    )
    pipeline = SearchPipeline()
    entry = await pipeline.run("python gil", app_config)
    assert entry.summary == "Summary"
    assert entry.category == "programming"


@pytest.mark.asyncio
async def test_pipeline_raises_on_empty_results(mocker, app_config) -> None:
    provider = mocker.patch("seekflow.workflows.builtin.ProviderRegistry.get").return_value
    provider.is_available.return_value = True
    provider.search.return_value = []
    pipeline = SearchPipeline()
    with pytest.raises(NoResultsError):
        await pipeline.run("missing", app_config)


@pytest.mark.asyncio
async def test_pipeline_raises_when_provider_is_unavailable(mocker, app_config) -> None:
    provider = mocker.patch("seekflow.workflows.builtin.ProviderRegistry.get").return_value
    provider.is_available.return_value = False

    pipeline = SearchPipeline()

    with pytest.raises(ProviderNotConfiguredError):
        await pipeline.run("python gil", app_config)


@pytest.mark.asyncio
async def test_pipeline_delegates_to_builtin_search_workflow(mocker, app_config) -> None:
    runner_cls = mocker.patch("seekflow.pipeline.WorkflowRunner")
    final_entry = SimpleNamespace(answer="answer")
    runner_cls.return_value.run = AsyncMock(
        return_value=Artifact(name="saved_record", payload=final_entry)
    )

    pipeline = SearchPipeline()
    result = await pipeline.run("python gil", app_config)

    runner_cls.assert_called_once()
    assert result is final_entry


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
