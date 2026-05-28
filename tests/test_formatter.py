from rich.console import Console

from seekflow.output.formatter import SessionMessage, build_app_shell


def test_build_header_text_contains_session_fields(app_config) -> None:
    from seekflow.output.formatter import build_header_text

    header = build_header_text(app_config)

    assert "SeekFlow" in header
    assert "Welcome back!" in header
    assert "duckduckgo" in header
    assert "gpt-4o-mini" in header


def test_build_header_text_uses_single_welcome_card_layout(app_config) -> None:
    from seekflow.output.formatter import build_header_text

    header = build_header_text(app_config, width=100)

    assert header.startswith("╭")
    assert "Tips for getting started" in header
    assert "Recent activity" in header
    assert "╰" in header


def test_build_transcript_text_contains_roles_and_bodies() -> None:
    from seekflow.output.formatter import build_transcript_text

    transcript = build_transcript_text(
        [
            SessionMessage(role="user", title="You", body="What is Python GIL?"),
            SessionMessage(role="assistant", title="SeekFlow", body="The GIL is a CPython mutex."),
        ]
    )

    assert "› What is Python GIL?" in transcript
    assert "SeekFlow" in transcript
    assert "The GIL is a CPython mutex." in transcript


def test_build_repl_body_text_includes_header_and_transcript(app_config) -> None:
    from seekflow.output.formatter import build_repl_body_text

    body = build_repl_body_text(
        app_config,
        [
            SessionMessage(role="user", title="You", body="hello"),
            SessionMessage(role="assistant", title="SeekFlow", body="hi"),
        ],
        width=100,
    )

    assert "Welcome back!" in body
    assert "› hello" in body
    assert "SeekFlow" in body


def test_build_transcript_text_keeps_older_messages() -> None:
    from seekflow.output.formatter import build_transcript_text

    messages = [
        SessionMessage(role="system", title=f"Message {index}", body=f"body {index}")
        for index in range(12)
    ]

    transcript = build_transcript_text(messages)

    assert "Message 0" in transcript
    assert "Message 11" in transcript


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
