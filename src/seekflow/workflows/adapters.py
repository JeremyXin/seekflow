from __future__ import annotations

import asyncio

from seekflow.workflows.models import Artifact


async def _run_command(command: list[str], stdin_text: str | None = None) -> tuple[str, str, int]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate(stdin_text.encode() if stdin_text is not None else None)
    return stdout.decode(), stderr.decode(), process.returncode


class CommandAdapter:
    def __init__(self, command: list[str], output_name: str) -> None:
        self.command = command
        self.output_name = output_name

    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        stdin_text = ""
        if artifact is not None:
            stdin_text = artifact.payload if isinstance(artifact.payload, str) else str(artifact.payload)

        try:
            stdout, stderr, returncode = await _run_command(self.command, stdin_text=stdin_text)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Command adapter executable not found: {self.command[0]}") from exc
        if returncode != 0:
            raise RuntimeError(stderr.strip() or "Command adapter failed.")

        output = stdout.strip()
        if not output:
            raise RuntimeError("Command adapter returned empty output.")

        return Artifact(
            name=self.output_name,
            payload=output,
            meta={"command": self.command},
        )


class SkillAdapter(CommandAdapter):
    def __init__(self, skill_name: str, output_name: str) -> None:
        super().__init__(command=["skill", skill_name], output_name=output_name)
        self.skill_name = skill_name

    async def run(self, artifact: Artifact | None, context: dict) -> Artifact:
        command = context.get("skill_commands", {}).get(self.skill_name, self.command)
        original_command = self.command
        self.command = command
        try:
            return await super().run(artifact, context)
        finally:
            self.command = original_command
