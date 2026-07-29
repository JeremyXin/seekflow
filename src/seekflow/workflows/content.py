from __future__ import annotations

from datetime import UTC, datetime

from seekflow.knowledge.writer import save_entry
from seekflow.models import KBEntry
from seekflow.workflows.adapters import SkillAdapter
from seekflow.workflows.builtin import (
    CollectSearchResultsStep,
    ExtractDocumentsStep,
    SynthesizeBriefStep,
)
from seekflow.workflows.models import Artifact, BackendBinding, StepSpec, WorkflowSpec


class BriefToOutlineStep:
    def __init__(self, skill_name: str = "blog-outline-creator") -> None:
        self.adapter = SkillAdapter(skill_name=skill_name, output_name="outline")

    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        assert artifact is not None
        context["brief_entry"] = artifact.payload
        outline_artifact = await self.adapter.run(artifact, context)
        context["outline_artifact"] = outline_artifact
        return outline_artifact


class OutlineToArticleStep:
    def __init__(self, skill_name: str = "blog-writer") -> None:
        self.adapter = SkillAdapter(skill_name=skill_name, output_name="article")

    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        article_artifact = await self.adapter.run(artifact, context)
        context["article_artifact"] = article_artifact
        return article_artifact


class SaveArticleStep:
    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        assert artifact is not None
        config = context["config"]
        brief_entry: KBEntry = context["brief_entry"]
        article_text = artifact.payload if isinstance(artifact.payload, str) else str(artifact.payload)
        summary = article_text.strip().replace("\n", " ")[:140]
        entry = KBEntry(
            title=brief_entry.title,
            date=datetime.now(UTC),
            query=brief_entry.query,
            answer=article_text,
            tags=list(dict.fromkeys([*brief_entry.tags, "article"])),
            category=brief_entry.category,
            provider=brief_entry.provider,
            model=config.llm.model,
            summary=summary or brief_entry.summary,
            sources=brief_entry.sources,
        )
        await save_entry(
            entry,
            config.knowledge_base.kb_dir,
            obsidian_mode=config.knowledge_base.obsidian_mode,
        )
        context["article_entry"] = entry
        return Artifact(name="saved_record", payload=entry)


def build_search_to_article_spec() -> WorkflowSpec:
    return WorkflowSpec(
        name="search_to_article",
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
            StepSpec(
                name="brief_to_outline",
                role="transformer",
                consumes="kb_entry",
                produces="outline",
                backend=BackendBinding(kind="skill_adapter", target="blog-outline-creator"),
            ),
            StepSpec(
                name="outline_to_article",
                role="transformer",
                consumes="outline",
                produces="article",
                backend=BackendBinding(kind="skill_adapter", target="blog-writer"),
            ),
            StepSpec(name="save_article", role="sink", consumes="article", produces="saved_record"),
        ],
    )


def build_search_to_article_steps() -> dict[str, object]:
    return {
        "collect_search_results": CollectSearchResultsStep(),
        "extract_documents": ExtractDocumentsStep(),
        "synthesize_brief": SynthesizeBriefStep(),
        "brief_to_outline": BriefToOutlineStep(),
        "outline_to_article": OutlineToArticleStep(),
        "save_article": SaveArticleStep(),
    }


def build_brief_to_article_spec() -> WorkflowSpec:
    return WorkflowSpec(
        name="brief_to_article",
        steps=[
            StepSpec(
                name="brief_to_outline",
                role="transformer",
                consumes="kb_entry",
                produces="outline",
                backend=BackendBinding(kind="skill_adapter", target="blog-outline-creator"),
            ),
            StepSpec(
                name="outline_to_article",
                role="transformer",
                consumes="outline",
                produces="article",
                backend=BackendBinding(kind="skill_adapter", target="blog-writer"),
            ),
            StepSpec(name="save_article", role="sink", consumes="article", produces="saved_record"),
        ],
    )


def build_brief_to_article_steps() -> dict[str, object]:
    return {
        "brief_to_outline": BriefToOutlineStep(),
        "outline_to_article": OutlineToArticleStep(),
        "save_article": SaveArticleStep(),
    }
