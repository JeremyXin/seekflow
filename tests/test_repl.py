import pytest
from types import SimpleNamespace
from prompt_toolkit.data_structures import Point
from prompt_toolkit.document import Document
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

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
    assert "PgUp/PgDn scroll transcript" in prompt
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
    prompt_factory = tui.input_area.control.input_processors[2].text
    assert "[chat]" in prompt_factory()[0][1]


def test_mode_prompt_is_dynamic(app_config, tmp_path) -> None:
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

    prompt_factory = tui.input_area.control.input_processors[2].text
    assert "[search]" in prompt_factory()[0][1]

    set_mode("chat")

    assert "[chat]" in prompt_factory()[0][1]


def test_mode_command_completion_offers_subcommands(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    completions = [
        completion.text
        for completion in tui.input_area.completer.get_completions(Document("/mode ", len("/mode ")), None)
    ]

    assert completions == ["status", "chat", "search"]


def test_pageup_scrolls_transcript_without_changing_input(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "draft input"
    tui.body_area.window.vertical_scroll = 20

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("pageup",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert tui.body_area.window.vertical_scroll < 20
    assert tui.input_area.text == "draft input"
    assert tui._follow_output is False


def test_ctrl_up_scrolls_transcript_in_small_steps(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.body_area.window.vertical_scroll = 20

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("c-up",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert tui.body_area.window.vertical_scroll == 17
    assert tui._follow_output is False


def test_mouse_support_is_enabled_for_trackpad_scroll(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert tui.application.mouse_support()


@pytest.mark.parametrize(
    ("event_type", "starting_scroll", "expected_scroll"),
    [
        (MouseEventType.SCROLL_UP, 20, 17),
        (MouseEventType.SCROLL_DOWN, 20, 23),
    ],
)
def test_mouse_scroll_on_input_area_scrolls_transcript(
    app_config,
    tmp_path,
    event_type,
    starting_scroll,
    expected_scroll,
) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "draft input"
    tui.body_area.window.vertical_scroll = starting_scroll
    tui.application.layout.focus(tui.input_area)

    tui.input_area.control.mouse_handler(
        MouseEvent(
            position=Point(x=0, y=0),
            event_type=event_type,
            button=MouseButton.NONE,
            modifiers=frozenset(),
        )
    )

    assert tui.body_area.window.vertical_scroll == expected_scroll
    assert tui.input_area.text == "draft input"
    assert tui.application.layout.current_control == tui.input_area.control
    assert tui._follow_output is False


def test_refresh_preserves_scroll_position_when_follow_output_disabled(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.body_area.window.vertical_scroll = 12
    tui._follow_output = False
    tui.messages.append(SessionMessage(role="assistant", title="SeekFlow", body="new reply"))

    tui.refresh(refresh_header=False)

    assert tui.body_area.window.vertical_scroll == 12
