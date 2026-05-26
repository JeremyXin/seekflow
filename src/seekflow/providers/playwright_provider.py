import importlib
from urllib.parse import quote_plus

from seekflow.models import SearchResult
from seekflow.providers.base import SearchProvider
from seekflow.providers.registry import ProviderRegistry


@ProviderRegistry.register
class PlaywrightProvider(SearchProvider):
    name = "playwright"

    async def is_available(self) -> bool:
        try:
            importlib.import_module("playwright.async_api")
        except ImportError:
            return False
        return True

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.config.headless)
            page = await browser.new_page()
            await page.goto(
                f"https://www.bing.com/search?q={quote_plus(query[:400])}",
                wait_until="domcontentloaded",
            )
            rows = await page.locator("#b_results .b_algo").all()
            results: list[SearchResult] = []
            for row in rows[:num_results]:
                anchor = row.locator("h2 a")
                snippet = row.locator(".b_caption p")
                results.append(
                    SearchResult(
                        url=await anchor.get_attribute("href") or "",
                        title=await anchor.inner_text(),
                        snippet=await snippet.inner_text() if await snippet.count() else "",
                        provider=self.name,
                    )
                )
            await browser.close()
            return results
