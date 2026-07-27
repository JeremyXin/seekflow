from __future__ import annotations

import inspect

from seekflow.workflows.models import Artifact, WorkflowSpec


class WorkflowRunner:
    def __init__(self, spec: WorkflowSpec, step_impls: dict[str, object]) -> None:
        self.spec = spec
        self.step_impls = step_impls

    async def run(self, initial_artifact: Artifact | None, context: dict) -> Artifact:
        artifact = initial_artifact
        for step in self.spec.steps:
            impl = self.step_impls[step.name]
            result = impl.run(artifact, context)
            if inspect.isawaitable(result):
                result = await result
            artifact = result
        if artifact is None:
            raise RuntimeError(f"Workflow {self.spec.name} produced no final artifact")
        return artifact
