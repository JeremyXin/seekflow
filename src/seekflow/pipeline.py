import inspect
from datetime import UTC, datetime

from seekflow.errors import NoResultsError, ProviderNotConfiguredError
from seekflow.extraction.extractor import extract_content
from seekflow.knowledge.writer import save_entry
from seekflow.models import KBEntry
import seekflow.providers  # noqa: F401
from seekflow.providers.registry import ProviderRegistry
from seekflow.synthesis.synthesizer import generate_metadata, synthesize_answer


class SearchPipeline:
    async def run(self, query: str, config, on_chunk=None, on_sources=None) -> KBEntry:
        provider = ProviderRegistry.get(
            config.app.default_provider,
            config.providers[config.app.default_provider],
        )
        available = provider.is_available()
        if inspect.isawaitable(available):
            available = await available
        if not available:
            raise ProviderNotConfiguredError(f"Provider {provider.name} is not available")

        results = provider.search(query, num_results=config.app.max_results)
        if inspect.isawaitable(results):
            results = await results
        if not results:
            raise NoResultsError("No search results. Try a different query or switch provider.")

        if on_sources:
            on_sources(results)

        for item in results[: config.app.extract_top_n]:
            content = extract_content(item.url)
            if inspect.isawaitable(content):
                content = await content
            item.content = content

        chunks: list[str] = []
        async for chunk in synthesize_answer(query, results, config):
            chunks.append(chunk)
            if on_chunk:
                on_chunk(chunk)

        answer = "".join(chunks).strip()
        metadata = generate_metadata(query, answer, config)
        if inspect.isawaitable(metadata):
            metadata = await metadata
        entry = KBEntry(
            title=query,
            date=datetime.now(UTC),
            query=query,
            answer=answer,
            tags=list(metadata["tags"]),
            category=str(metadata["category"]),
            provider=provider.name,
            model=config.llm.model,
            summary=str(metadata["summary"]),
            sources=results,
        )
        saved = save_entry(
            entry,
            config.knowledge_base.kb_dir,
            obsidian_mode=config.knowledge_base.obsidian_mode,
        )
        if inspect.isawaitable(saved):
            await saved
        return entry
