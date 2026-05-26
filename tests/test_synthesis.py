from seekflow.models import SearchResult
from seekflow.synthesis.synthesizer import build_context, classify_category


def test_build_context_keeps_citations() -> None:
    results = [
        SearchResult(
            url="https://example.com",
            title="Example",
            snippet="Snippet",
            content="Full content",
        )
    ]
    context = build_context("python gil", results, max_words=200)
    assert "[1]" in context
    assert "https://example.com" in context


def test_classify_category_is_rule_based() -> None:
    assert classify_category("How does kubernetes deployment work?") == "devops"
