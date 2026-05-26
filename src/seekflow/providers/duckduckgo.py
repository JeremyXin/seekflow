from ddgs import DDGS

from seekflow.models import SearchResult
from seekflow.providers.base import SearchProvider
from seekflow.providers.registry import ProviderRegistry


@ProviderRegistry.register
class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    async def is_available(self) -> bool:
        return True

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        rows = list(DDGS.text(DDGS(), query[:400], max_results=num_results))
        return [
            SearchResult(
                url=row["href"],
                title=row["title"],
                snippet=row.get("body", ""),
                provider=self.name,
            )
            for row in rows
        ]
