import pytest
from types import SimpleNamespace

from seekflow.output.formatter import SessionMessage
from seekflow.repl.session import SeekFlowTUI, build_input_hint_text, dispatch_input


@pytest.mark.asyncio
async def test_dispatches_slash_command() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("/help", fake_command, fake_chat, fake_search, lambda: "search")
    assert calls == [("command", "/help")]


@pytest.mark.asyncio
async def test_dispatches_search_query_in_search_mode() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("python gil", fake_command, fake_chat, fake_search, lambda: "search")
    assert calls == [("search", "python gil")]


@pytest.mark.asyncio
async def test_dispatches_chat_query_in_chat_mode() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("explain descriptors", fake_command, fake_chat, fake_search, lambda: "chat")
    assert calls == [("chat", "explain descriptors")]


def test_build_input_hint_text_contains_repl_guidance() -> None:
    prompt = build_input_hint_text("search")
    assert "Shift-Tab toggle mode" in prompt
    assert "/mode" in prompt
    assert "search" in prompt


def test_build_repl_view_returns_text_sections(app_config) -> None:
    from seekflow.repl.session import build_repl_view

    sections = build_repl_view(
        app_config,
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        "draft input",
        "chat",
    )

    assert "SeekFlow" in sections["body"]
    assert "hello" in sections["body"]
    assert "draft input" in sections["input"]


def test_body_area_does_not_force_full_height(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="short reply")],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert tui.body_area.window.dont_extend_height()


def test_append_stream_chunk_builds_assistant_message() -> None:
    from seekflow.repl.session import append_stream_chunk

    messages: list[SessionMessage] = []

    append_stream_chunk(messages, "Hello")
    append_stream_chunk(messages, " world")

    assert messages[-1].role == "assistant"
    assert messages[-1].body == "Hello world"


@pytest.mark.asyncio
async def test_submit_exception_becomes_error_message_and_restores_input(app_config, tmp_path) -> None:
    async def failing_command(text: str) -> None:
        raise RuntimeError(f"boom: {text}")

    async def unused_search(text: str) -> None:
        raise AssertionError("search handler should not be called")

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        failing_command,
        unused_search,
        unused_search,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "/help"

    await tui._submit_current_input()

    assert tui.input_area.text == "/help"
    assert tui.messages[-1].role == "error"
    assert "boom: /help" in tui.messages[-1].body


def test_shift_tab_toggles_mode_and_updates_prompt(app_config, tmp_path) -> None:
    mode = "search"

    def get_mode() -> str:
        return mode

    def set_mode(new_mode: str) -> None:
        nonlocal mode
        mode = new_mode

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        get_mode,
        set_mode,
    )

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("s-tab",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert mode == "chat"
    assert "[chat]" in tui.input_area.prompt[0][1]
