from datetime import datetime

from seekflow.knowledge.writer import render_markdown, slugify_query
from seekflow.models import KBEntry, SearchResult


def test_slugify_query_strips_symbols() -> None:
    assert slugify_query("What is C++? (2026 edition)") == "what-is-c-2026-edition"


def test_render_markdown_contains_frontmatter() -> None:
    entry = KBEntry(
        title="Python GIL",
        date=datetime(2026, 5, 26, 12, 0, 0),
        query="What is Python GIL?",
        answer="GIL explanation [1].",
        tags=["python"],
        category="programming",
        provider="duckduckgo",
        model="gpt-4o-mini",
        summary="GIL summary",
        sources=[SearchResult(url="https://example.com", title="Example", snippet="Snippet")],
    )
    content = render_markdown(entry, obsidian_mode=False)
    assert content.startswith("---")
    assert "## Answer" in content
    assert "## Sources" in content
