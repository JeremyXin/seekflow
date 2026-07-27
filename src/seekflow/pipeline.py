from seekflow.models import KBEntry
from seekflow.workflows.builtin import build_search_to_brief_spec, build_search_to_brief_steps
from seekflow.workflows.models import Artifact
from seekflow.workflows.runner import WorkflowRunner


class SearchPipeline:
    async def run(self, query: str, config, on_chunk=None, on_sources=None) -> KBEntry:
        runner = WorkflowRunner(build_search_to_brief_spec(), build_search_to_brief_steps())
        final_artifact = await runner.run(
            initial_artifact=Artifact(name="query", payload=query),
            context={
                "config": config,
                "on_chunk": on_chunk,
                "on_sources": on_sources,
            },
        )
        return final_artifact.payload
