from seekflow.workflows.models import Artifact, StepSpec, WorkflowSpec


def test_artifact_store_preserves_type_name_and_payload() -> None:
    artifact = Artifact(name="search_results", payload={"items": [1, 2, 3]})

    assert artifact.name == "search_results"
    assert artifact.payload == {"items": [1, 2, 3]}


def test_workflow_spec_requires_linear_step_order() -> None:
    spec = WorkflowSpec(
        name="search_to_brief",
        steps=[
            StepSpec(name="collect", role="collector", consumes=None, produces="search_results"),
            StepSpec(name="summarize", role="transformer", consumes="search_results", produces="research_brief"),
            StepSpec(name="save", role="sink", consumes="research_brief", produces="saved_record"),
        ],
    )

    assert [step.name for step in spec.steps] == ["collect", "summarize", "save"]
