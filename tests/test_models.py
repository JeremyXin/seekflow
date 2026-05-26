from seekflow.models import SearchResult


def test_search_result_defaults() -> None:
    result = SearchResult(url="https://example.com", title="Example", snippet="demo")
    assert result.content is None
    assert result.provider == ""
