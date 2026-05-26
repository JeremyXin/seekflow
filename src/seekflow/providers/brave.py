import httpx

from seekflow.models import SearchResult
from seekflow.providers.base import SearchProvider
from seekflow.providers.registry import ProviderRegistry


@ProviderRegistry.register
class BraveSearchProvider(SearchProvider):
    name = "brave"

    async def is_available(self) -> bool:
        return bool(self.config.api_key)

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query[:400], "count": num_results},
                headers={"X-Subscription-Token": self.config.api_key or ""},
            )
            response.raise_for_status()
        payload = response.json()
        return [
            SearchResult(
                url=item["url"],
                title=item["title"],
                snippet=item.get("description", ""),
                provider=self.name,
            )
            for item in payload.get("web", {}).get("results", [])
        ]
