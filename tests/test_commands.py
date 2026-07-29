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

    await handle_command("/help", app_config, emit, get_mode=lambda: "search", set_mode=lambda mode: None)
    assert any("/mode search" in line for line in output)


@pytest.mark.asyncio
async def test_provider_switch_updates_runtime_config(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command("/provider switch duckduckgo", app_config, emit, get_mode=lambda: "search", set_mode=lambda mode: None)
    assert app_config.app.default_provider == "duckduckgo"
    assert any("Switched" in item for item in output)


@pytest.mark.asyncio
async def test_save_command_reports_missing_chat(app_config) -> None:
    output = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command(
        "/save",
        app_config,
        emit,
        latest_chat=None,
        get_mode=lambda: "search",
        set_mode=lambda mode: None,
    )
    assert output == ["No chat exchange available to save."]


@pytest.mark.asyncio
async def test_save_command_persists_latest_chat(mocker, app_config, tmp_path) -> None:
    output: list[str] = []
    expected_path = tmp_path / "saved-chat.md"
    mock_save = mocker.patch("seekflow.repl.commands.save_entry")
    mock_save.return_value = expected_path

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command(
        "/save",
        app_config,
        emit,
        latest_chat=("What is the GIL?", "The GIL is a CPython interpreter lock."),
        get_mode=lambda: "search",
        set_mode=lambda mode: None,
    )

    mock_save.assert_awaited_once()
    assert output == [f"Saved chat to {expected_path}"]


@pytest.mark.asyncio
async def test_mode_status_reports_current_mode(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command("/mode status", app_config, emit, get_mode=lambda: "chat", set_mode=lambda mode: None)

    assert output == ["Current mode: chat"]


@pytest.mark.asyncio
async def test_mode_switch_updates_session_mode(app_config) -> None:
    output: list[str] = []
    mode = "search"

    async def emit(text: str) -> None:
        output.append(text)

    def get_mode() -> str:
        return mode

    def set_mode(new_mode: str) -> None:
        nonlocal mode
        mode = new_mode

    await handle_command("/mode chat", app_config, emit, get_mode=get_mode, set_mode=set_mode)

    assert mode == "chat"
    assert output == ["Switched mode to chat"]


@pytest.mark.asyncio
async def test_mode_rejects_invalid_target(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    await handle_command("/mode invalid", app_config, emit, get_mode=lambda: "search", set_mode=lambda mode: None)

    assert output == ["Usage: /mode status|chat|search"]


@pytest.mark.asyncio
async def test_workflow_list_command_reports_available_workflows(app_config) -> None:
    output: list[str] = []

    async def emit(text: str) -> None:
        output.append(text)

    async def run_workflow(action: str, name: str, value: str | None = None) -> None:
        return None

    await handle_command(
        "/workflow list",
        app_config,
        emit,
        workflow_handler=run_workflow,
        get_mode=lambda: "search",
        set_mode=lambda mode: None,
    )

    assert output == ["Workflows: search_to_article"]


@pytest.mark.asyncio
async def test_workflow_continue_delegates_to_workflow_handler(app_config) -> None:
    calls: list[tuple[str, str, str | None]] = []

    async def emit(text: str) -> None:
        return None

    async def run_workflow(action: str, name: str, value: str | None = None) -> None:
        calls.append((action, name, value))

    await handle_command(
        "/workflow continue search_to_article",
        app_config,
        emit,
        workflow_handler=run_workflow,
        get_mode=lambda: "search",
        set_mode=lambda mode: None,
    )

    assert calls == [("continue", "search_to_article", None)]
