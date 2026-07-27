import pytest

from seekflow.workflows.models import Artifact, StepSpec, WorkflowSpec
from seekflow.workflows.runner import WorkflowRunner


class FakeCollectStep:
    async def run(self, artifact, context):
        return Artifact(name="search_results", payload=["result-a", "result-b"])


class FakeTransformStep:
    async def run(self, artifact, context):
        assert artifact.name == "search_results"
        return Artifact(name="research_brief", payload="brief")


@pytest.mark.asyncio
async def test_runner_executes_linear_steps_in_order() -> None:
    spec = WorkflowSpec(
        name="search_to_brief",
        steps=[
            StepSpec(name="collect", role="collector", consumes=None, produces="search_results"),
            StepSpec(name="summarize", role="transformer", consumes="search_results", produces="research_brief"),
        ],
    )
    runner = WorkflowRunner(
        spec,
        step_impls={"collect": FakeCollectStep(), "summarize": FakeTransformStep()},
    )

    result = await runner.run(initial_artifact=Artifact(name="query", payload="python gil"), context={})

    assert result.name == "research_brief"
    assert result.payload == "brief"


@pytest.mark.asyncio
async def test_runner_raises_when_step_impl_is_missing() -> None:
    spec = WorkflowSpec(
        name="search_to_brief",
        steps=[StepSpec(name="collect", role="collector", consumes=None, produces="search_results")],
    )
    runner = WorkflowRunner(spec, step_impls={})

    with pytest.raises(KeyError):
        await runner.run(initial_artifact=None, context={})
