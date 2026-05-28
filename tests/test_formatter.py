from rich.console import Console

from seekflow.output.formatter import SessionMessage, build_app_shell


def test_build_app_shell_renders_header_and_chat_sections(app_config) -> None:
    console = Console(record=True, width=140)
    messages = [
        SessionMessage(role="user", title="You", body="What is Python GIL?"),
        SessionMessage(role="assistant", title="SeekFlow", body="The GIL is a CPython mutex."),
    ]

    console.print(build_app_shell(app_config, messages))
    output = console.export_text()

    assert "Welcome" in output
    assert "provider: duckduckgo" in output
    assert "model: gpt-4o-mini" in output
    assert "Session" in output
    assert "Knowledge base:" in output
    assert "What is Python GIL?" in output
    assert "The GIL is a CPython mutex." in output


def test_router_event_message_is_rendered(app_config) -> None:
    from seekflow.output.formatter import SessionMessage, build_app_shell

    message = SessionMessage(
        role="tool",
        title="Web Search",
        body="Reason: current external information required",
    )
    shell = build_app_shell(app_config, [message])
    console = Console(record=True, width=140)
    console.print(shell)
    assert "Web Search" in console.export_text()
