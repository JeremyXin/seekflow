import pytest

from seekflow.repl.commands import handle_command, parse_command


def test_parse_command_splits_name_and_args() -> None:
    command, args = parse_command("/provider switch duckduckgo")
    assert command == "provider"
    assert args == ["switch", "duckduckgo"]


@pytest.mark.asyncio
async def test_help_command_returns_known_commands(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command("/help", app_config, emit)
    assert any("/kb list" in line for line in output)


@pytest.mark.asyncio
async def test_provider_switch_updates_runtime_config(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command("/provider switch duckduckgo", app_config, emit)
    assert app_config.app.default_provider == "duckduckgo"
    assert any("Switched" in item for item in output)
