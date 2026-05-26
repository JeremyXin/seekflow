import httpx

from seekflow.models import SearchResult
from seekflow.providers.base import SearchProvider
from seekflow.providers.registry import ProviderRegistry


@ProviderRegistry.register
class SerpApiProvider(SearchProvider):
    name = "serpapi"

    async def is_available(self) -> bool:
        return bool(self.config.api_key)

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": query[:400],
                    "num": num_results,
                    "api_key": self.config.api_key or "",
                },
            )
            response.raise_for_status()
        payload = response.json()
        return [
            SearchResult(
                url=item["link"],
                title=item["title"],
                snippet=item.get("snippet", ""),
                provider=self.name,
            )
            for item in payload.get("organic_results", [])
        ]
