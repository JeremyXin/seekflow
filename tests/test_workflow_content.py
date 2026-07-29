from datetime import UTC, datetime

import pytest

from seekflow.models import KBEntry
from seekflow.workflows.content import SaveArticleStep, build_search_to_article_spec
from seekflow.workflows.models import Artifact, BackendBinding, StepSpec
from seekflow.repl.workflows import WorkflowSessionState


def test_step_spec_can_store_backend_binding() -> None:
    step = StepSpec(
        name="brief_to_outline",
        role="transformer",
        consumes="kb_entry",
        produces="outline",
        backend=BackendBinding(kind="skill_adapter", target="blog-outline-creator"),
    )

    assert step.backend.kind == "skill_adapter"
    assert step.backend.target == "blog-outline-creator"


def test_search_to_article_spec_contains_content_steps() -> None:
    spec = build_search_to_article_spec()

    assert [step.name for step in spec.steps] == [
        "collect_search_results",
        "extract_documents",
        "synthesize_brief",
        "brief_to_outline",
        "outline_to_article",
        "save_article",
    ]


def test_workflow_session_state_tracks_latest_brief() -> None:
    state = WorkflowSessionState()
    state.latest_workflow_name = "search_to_article"
    state.latest_brief_entry = "brief"

    assert state.latest_workflow_name == "search_to_article"
    assert state.latest_brief_entry == "brief"


@pytest.mark.asyncio
async def test_save_article_step_persists_article_entry(mocker, app_config, tmp_path) -> None:
    brief_entry = KBEntry(
        title="python gil",
        date=datetime.now(UTC),
        query="python gil",
        answer="brief",
        tags=["python"],
        category="programming",
        provider="duckduckgo",
        model=app_config.llm.model,
        summary="brief summary",
        sources=[],
    )
    expected_path = tmp_path / "article.md"
    mock_save = mocker.patch("seekflow.workflows.content.save_entry")
    mock_save.return_value = expected_path
    step = SaveArticleStep()

    artifact = await step.run(
        Artifact(name="article", payload="full article body"),
        context={"config": app_config, "brief_entry": brief_entry},
    )

    saved_entry = artifact.payload
    assert artifact.name == "saved_record"
    assert saved_entry.answer == "full article body"
    assert saved_entry.query == "python gil"
    mock_save.assert_awaited_once()
