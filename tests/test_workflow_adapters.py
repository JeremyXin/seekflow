import pytest

from seekflow.workflows.adapters import CommandAdapter, SkillAdapter
from seekflow.workflows.models import Artifact


@pytest.mark.asyncio
async def test_command_adapter_returns_transformed_artifact(mocker) -> None:
    adapter = CommandAdapter(command=["echo", "outline text"], output_name="outline")
    mocker.patch("seekflow.workflows.adapters._run_command", return_value=("outline text", "", 0))

    artifact = await adapter.run(Artifact(name="kb_entry", payload="brief"), context={})

    assert artifact.name == "outline"
    assert artifact.payload == "outline text"


@pytest.mark.asyncio
async def test_skill_adapter_is_a_command_adapter_specialization(mocker) -> None:
    adapter = SkillAdapter(skill_name="blog-outline-creator", output_name="outline")
    mocker.patch("seekflow.workflows.adapters._run_command", return_value=("outline text", "", 0))

    artifact = await adapter.run(Artifact(name="kb_entry", payload="brief"), context={})

    assert artifact.name == "outline"


@pytest.mark.asyncio
async def test_command_adapter_raises_on_non_zero_exit(mocker) -> None:
    adapter = CommandAdapter(command=["false"], output_name="outline")
    mocker.patch("seekflow.workflows.adapters._run_command", return_value=("", "boom", 1))

    with pytest.raises(RuntimeError, match="boom"):
        await adapter.run(Artifact(name="kb_entry", payload="brief"), context={})


@pytest.mark.asyncio
async def test_command_adapter_raises_on_empty_stdout(mocker) -> None:
    adapter = CommandAdapter(command=["echo"], output_name="outline")
    mocker.patch("seekflow.workflows.adapters._run_command", return_value=("", "", 0))

    with pytest.raises(RuntimeError, match="empty output"):
        await adapter.run(Artifact(name="kb_entry", payload="brief"), context={})
