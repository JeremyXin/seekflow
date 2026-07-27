from __future__ import annotations

import inspect
from datetime import UTC, datetime

from seekflow.errors import NoResultsError, ProviderNotConfiguredError
from seekflow.extraction.extractor import extract_content
from seekflow.knowledge.writer import save_entry
from seekflow.models import KBEntry
import seekflow.providers  # noqa: F401
from seekflow.providers.registry import ProviderRegistry
from seekflow.synthesis.synthesizer import generate_metadata, synthesize_answer
from seekflow.workflows.models import Artifact, StepSpec, WorkflowSpec


async def _resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value


class CollectSearchResultsStep:
    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        query = artifact.payload if artifact is not None else ""
        config = context["config"]
        provider = ProviderRegistry.get(
            config.app.default_provider,
            config.providers[config.app.default_provider],
        )
        available = await _resolve(provider.is_available())
        if not available:
            raise ProviderNotConfiguredError(f"Provider {provider.name} is not available")

        results = await _resolve(provider.search(query, num_results=config.app.max_results))
        if not results:
            raise NoResultsError("No search results. Try a different query or switch provider.")

        on_sources = context.get("on_sources")
        if on_sources:
            on_sources(results)

        context["provider_name"] = provider.name
        context["query"] = query
        return Artifact(name="search_results", payload=results)


class ExtractDocumentsStep:
    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        assert artifact is not None
        config = context["config"]
        results = artifact.payload

        for item in results[: config.app.extract_top_n]:
            item.content = await _resolve(extract_content(item.url))

        return Artifact(name="extracted_documents", payload=results)


class SynthesizeBriefStep:
    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        assert artifact is not None
        config = context["config"]
        query = context["query"]
        results = artifact.payload
        on_chunk = context.get("on_chunk")

        chunks: list[str] = []
        async for chunk in synthesize_answer(query, results, config):
            chunks.append(chunk)
            if on_chunk:
                on_chunk(chunk)

        answer = "".join(chunks).strip()
        metadata = await _resolve(generate_metadata(query, answer, config))
        entry = KBEntry(
            title=query,
            date=datetime.now(UTC),
            query=query,
            answer=answer,
            tags=list(metadata["tags"]),
            category=str(metadata["category"]),
            provider=context["provider_name"],
            model=config.llm.model,
            summary=str(metadata["summary"]),
            sources=results,
        )
        return Artifact(name="kb_entry", payload=entry)


class SaveKBEntryStep:
    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        assert artifact is not None
        config = context["config"]
        entry: KBEntry = artifact.payload
        await _resolve(
            save_entry(
                entry,
                config.knowledge_base.kb_dir,
                obsidian_mode=config.knowledge_base.obsidian_mode,
            )
        )
        return Artifact(name="saved_record", payload=entry)


def build_search_to_brief_spec() -> WorkflowSpec:
    return WorkflowSpec(
        name="search_to_brief",
        steps=[
            StepSpec(name="collect_search_results", role="collector", consumes="query", produces="search_results"),
            StepSpec(
                name="extract_documents",
                role="transformer",
                consumes="search_results",
                produces="extracted_documents",
            ),
            StepSpec(
                name="synthesize_brief",
                role="transformer",
                consumes="extracted_documents",
                produces="kb_entry",
            ),
            StepSpec(name="save_kb_entry", role="sink", consumes="kb_entry", produces="saved_record"),
        ],
    )


def build_search_to_brief_steps() -> dict[str, object]:
    return {
        "collect_search_results": CollectSearchResultsStep(),
        "extract_documents": ExtractDocumentsStep(),
        "synthesize_brief": SynthesizeBriefStep(),
        "save_kb_entry": SaveKBEntryStep(),
    }
